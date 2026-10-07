"""Fix the "Specaialization" field name and rename the role groups.

"docter" -> "doctor" and "user" -> "patient". Existing accounts keep their
role: the groups are renamed in place, so memberships are untouched.
"""

from django.db import migrations

RENAMES = [("docter", "doctor"), ("user", "patient")]


def rename_groups(apps, schema_editor, pairs):
    Group = apps.get_model("auth", "Group")
    for old, new in pairs:
        old_group = Group.objects.filter(name=old).first()
        if old_group is None:
            continue
        new_group = Group.objects.filter(name=new).first()
        if new_group is None:
            old_group.name = new
            old_group.save(update_fields=["name"])
        else:
            # Both exist: move members across, then drop the old group.
            for user in old_group.user_set.all():
                user.groups.add(new_group)
            old_group.delete()


def forwards(apps, schema_editor):
    rename_groups(apps, schema_editor, RENAMES)


def backwards(apps, schema_editor):
    rename_groups(apps, schema_editor, [(new, old) for old, new in RENAMES])


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0004_prescription_prescriptionfile_ocrresult_and_more"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RenameField(model_name="doctor", old_name="Specaialization", new_name="Specialization"),
        migrations.RunPython(forwards, backwards),
    ]
