from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('directory', '0003_add_kegiatan_jenis'),
    ]

    operations = [
        migrations.CreateModel(
            name='KomunitasAnggotaPending',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipe', models.CharField(choices=[('gabung', 'Permintaan gabung'), ('keluar', 'Permintaan keluar')], max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('komunitas', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='anggota_pending', to='directory.komunitas')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='komunitas_pending', to='directory.member')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='komunitasanggotapending',
            unique_together={('member', 'komunitas')},
        ),
    ]
