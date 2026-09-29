import json
import os

from django.http import JsonResponse


def api_wilayah(request):
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'wilayah.json')
    try:
        with open(data_path, encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return JsonResponse(
            {'error': 'Data wilayah belum dimuat. Jalankan: python manage.py fetch_wilayah'},
            status=503,
        )

    province_id = request.GET.get('province_id')
    if province_id:
        return JsonResponse({'regencies': data['regencies'].get(province_id, [])})
    return JsonResponse({'provinces': data['provinces']})
