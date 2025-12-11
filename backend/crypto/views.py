from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import LocalQKDKey


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def local_keys(request):
    """
    List cached local KM keys for monitoring.
    Query params:
      - limit: int (default 200)
    """
    try:
        limit = int(request.query_params.get("limit", "200"))
    except ValueError:
        limit = 200

    keys = (
        LocalQKDKey.objects.all()
        .order_by("-created_at")[:limit]
    )

    data = []
    for k in keys:
        data.append(
            {
                "key_id": k.key_id,
                "requester_sae": k.requester_sae,
                "recipient_sae": k.recipient_sae,
                "key_size": k.key_size,
                "algorithm": k.algorithm,
                "state": k.state,
                "created_at": k.created_at.isoformat() if k.created_at else None,
                "served_at": k.served_at.isoformat() if k.served_at else None,
                "consumed_at": k.consumed_at.isoformat() if k.consumed_at else None,
                "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                "key_material": k.key_material_b64,
            }
        )

    return JsonResponse({"keys": data})
