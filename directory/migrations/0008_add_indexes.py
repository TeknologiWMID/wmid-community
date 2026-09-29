from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('directory', '0007_add_komunitas_narahubung'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='kegiatananggota',
            index=models.Index(fields=['status'], name='ka_status_idx'),
        ),
        migrations.AddIndex(
            model_name='komunitasanggotapending',
            index=models.Index(fields=['tipe'], name='kap_tipe_idx'),
        ),
        migrations.AddIndex(
            model_name='member',
            index=models.Index(fields=['availability'], name='member_avail_idx'),
        ),
        migrations.AddIndex(
            model_name='member',
            index=models.Index(fields=['role'], name='member_role_idx'),
        ),
        migrations.AddIndex(
            model_name='contribution',
            index=models.Index(fields=['member', 'project'], name='contrib_member_project_idx'),
        ),
    ]
