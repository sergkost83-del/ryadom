from django.conf import settings
import functools

from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods
from rest_framework.exceptions import Throttled

from apps.audit.service import record, request_ip

from . import totp, twofactor
from .services import check_throttle


def _staff_only(view):
    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return redirect(reverse("admin:login"))
        return view(request, *args, **kwargs)

    return wrapper


def _next(request):
    target = request.POST.get("next") or request.GET.get("next") or ""
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return target
    return reverse("admin:index")


def _audit(request, action, note=""):
    record(actor=request.user, action=action, object_type="staff", object_id=request.user.pk,
           ip=request_ip(request), note=note)


def _qr(uri):
    try:
        import segno

        return segno.make(uri, error="m").svg_inline(scale=5, dark="#11192c")
    except Exception:  # noqa: BLE001  (без библиотеки покажем только ключ для ручного ввода)
        return ""


def _throttled(request):
    try:
        check_throttle("2fa-verify-user", str(request.user.pk), settings.ADMIN_2FA_ATTEMPTS_PER_15_MIN, 900)
    except Throttled:
        return True
    return False


@_staff_only
@require_http_methods(["GET", "POST"])
def setup(request):
    user = request.user
    if twofactor.confirmed_device(user):
        return redirect(reverse("twofactor-verify") if not twofactor.is_verified(request) else _next(request))
    device = twofactor.pending_device(user)
    error = ""
    if request.method == "POST":
        if _throttled(request):
            error = "Слишком много попыток. Подождите 15 минут."
        elif twofactor.confirm_device(user, request.POST.get("code", "")):
            codes = twofactor.issue_backup_codes(user)
            twofactor.mark_verified(request)
            _audit(request, "staff.2fa_enrolled")
            return render(request, "identity/backup_codes.html", {"codes": codes, "next": _next(request)})
        else:
            error = "Код не подошёл. Проверьте время на телефоне и попробуйте ещё раз."
            _audit(request, "staff.2fa_failed", note="подтверждение устройства")
    uri = totp.provisioning_uri(device.secret, user.email)
    return render(
        request,
        "identity/twofactor_setup.html",
        {"secret": device.secret, "qr_svg": _qr(uri), "error": error, "next": _next(request)},
    )


@_staff_only
@require_http_methods(["GET", "POST"])
def verify(request):
    user = request.user
    if not twofactor.confirmed_device(user):
        return redirect(reverse("twofactor-setup"))
    if twofactor.is_verified(request) and request.method == "GET":
        return redirect(_next(request))
    error = ""
    if request.method == "POST":
        if _throttled(request):
            error = "Слишком много попыток. Подождите 15 минут."
            _audit(request, "staff.2fa_throttled")
        else:
            kind = twofactor.verify_code(user, request.POST.get("code", ""))
            if kind:
                twofactor.mark_verified(request)
                _audit(request, "staff.2fa_verified" if kind == "totp" else "staff.2fa_backup_used")
                return redirect(_next(request))
            error = "Код не подошёл."
            _audit(request, "staff.2fa_failed")
    return render(
        request,
        "identity/twofactor_verify.html",
        {"error": error, "next": _next(request), "backup_left": twofactor.remaining_backup_codes(user)},
    )


@_staff_only
@require_http_methods(["POST"])
def regenerate_backup_codes(request):
    if not twofactor.is_verified(request):
        return redirect(reverse("twofactor-verify"))
    codes = twofactor.issue_backup_codes(request.user)
    _audit(request, "staff.2fa_backup_regenerated")
    return render(request, "identity/backup_codes.html", {"codes": codes, "next": reverse("admin:index")})
