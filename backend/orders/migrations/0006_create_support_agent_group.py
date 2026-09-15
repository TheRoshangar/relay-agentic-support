from django.db import migrations


def create_support_agent_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="support_agent")


def remove_support_agent_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="support_agent").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0005_rename_create_at_refundrequest_created_at"),  # آخرین migration واقعی orders رو جایگزین این کن
    ]

    operations = [
        migrations.RunPython(create_support_agent_group, remove_support_agent_group),
    ]