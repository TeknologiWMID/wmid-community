from .auth import email_login, logout, oauth_callback, oauth_login, register
from .profile import index, profile, profile_edit, profile_kegiatan_tambah, resync, riwayat_catat, riwayat_cancel
from .admin import (
    admin_anggota,
    admin_anggota_export,
    admin_anggota_detail,
    admin_anggota_edit,
    admin_dashboard,
    admin_kegiatan_assign,
    admin_kegiatan_data,
    admin_kegiatan_export,
    admin_kegiatan_import,
    admin_kegiatan_detail,
    admin_kegiatan_edit,
    admin_kegiatan_tambah,
    admin_kegiatan_list,
    admin_kegiatan_verify,
    admin_komunitas_verify,
    admin_komunitas,
    admin_komunitas_export,
    admin_komunitas_detail,
    admin_komunitas_edit,
)
from .komunitas import (
    komunitas_detail,
    komunitas_join,
    komunitas_leave,
    komunitas_list,
    komunitas_pending_cancel,
    sync_komunitas,
)
from .api import api_wilayah
from .kegiatan import (
    kegiatan_daftar,
    kegiatan_detail,
    kegiatan_list,
    sync_kegiatan,
)
