from django.urls import path

from . import views

urlpatterns = [
    path("auth/code/request/", views.RequestCodeView.as_view(), name="auth-code-request"),
    path("auth/code/verify/", views.VerifyCodeView.as_view(), name="auth-code-verify"),
    path("auth/register/", views.RegisterView.as_view(), name="auth-register"),
    path("auth/refresh/", views.RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/logout-all/", views.LogoutAllView.as_view(), name="auth-logout-all"),
    path("auth/sessions/", views.SessionListView.as_view(), name="auth-sessions"),
    path("auth/sessions/<uuid:pk>/", views.SessionDetailView.as_view(), name="auth-session-detail"),
    path("me/", views.MeView.as_view(), name="me"),
    path("legal/current/", views.LegalCurrentView.as_view(), name="legal-current"),
]
