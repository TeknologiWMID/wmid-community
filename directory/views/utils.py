from directory.models import Member


def get_session_member(request):
    member_id = request.session.get('member_id')
    if not member_id:
        return None
    try:
        return Member.objects.get(pk=member_id)
    except Member.DoesNotExist:
        request.session.pop('member_id', None)
        return None


def store_sync_result(request, result: dict):
    request.session['last_sync_result'] = {
        'saved':        result['saved'],
        'wikis_synced': result['wikis_synced'],
        'wikis_found':  result['wikis_found'],
        'errors':       result['errors'],
        'fallback':     result.get('fallback', False),
    }
