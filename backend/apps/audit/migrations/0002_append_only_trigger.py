from django.db import migrations

FORWARD = """
CREATE OR REPLACE FUNCTION audit_auditlog_protect() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'audit log is append-only';
  END IF;
  -- Разрешено только обнуление ссылок на пользователя и ЖК (когда они удаляются); содержимое менять нельзя.
  IF NEW.id IS DISTINCT FROM OLD.id
     OR NEW.created_at IS DISTINCT FROM OLD.created_at
     OR NEW.actor_email IS DISTINCT FROM OLD.actor_email
     OR NEW.action IS DISTINCT FROM OLD.action
     OR NEW.object_type IS DISTINCT FROM OLD.object_type
     OR NEW.object_id IS DISTINCT FROM OLD.object_id
     OR NEW.changes IS DISTINCT FROM OLD.changes
     OR NEW.ip_address IS DISTINCT FROM OLD.ip_address
     OR NEW.note IS DISTINCT FROM OLD.note
     OR (NEW.actor_id IS DISTINCT FROM OLD.actor_id AND NEW.actor_id IS NOT NULL)
     OR (NEW.community_id IS DISTINCT FROM OLD.community_id AND NEW.community_id IS NOT NULL) THEN
    RAISE EXCEPTION 'audit log is append-only';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_auditlog_protect_trg
BEFORE UPDATE OR DELETE ON audit_auditlog
FOR EACH ROW EXECUTE FUNCTION audit_auditlog_protect();
"""

REVERSE = """
DROP TRIGGER IF EXISTS audit_auditlog_protect_trg ON audit_auditlog;
DROP FUNCTION IF EXISTS audit_auditlog_protect();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(FORWARD, REVERSE),
    ]
