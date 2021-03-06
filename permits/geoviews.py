from . import models, services, serializers
from geomapshark import settings
import requests
from django.core.serializers import serialize
from django.db.models import Prefetch, Q
from django.http import JsonResponse, HttpResponseNotFound, FileResponse
from django.contrib.auth.decorators import login_required
import json
import urllib
from django.utils.translation import gettext_lazy as _
import datetime
from rest_framework import viewsets


@login_required
def qgisserver_proxy(request):

    # Secure QGISSERVER as it potentially has access to whole DB
    # Event getcapabilities requests are disabled
    if request.GET['REQUEST'] == 'GetMap':
        data = urllib.parse.urlencode(request.GET)
        format = request.GET['FORMAT']
        url = "http://qgisserver" + '/?' + data
        response = requests.get(url)
        return FileResponse(response, content_type=format)

    else:
        return HttpResponseNotFound(_('Seules les requêtes GetMap sur la couche' +
                                      'permits_permitadministrativeentity sont autorisées'))


@login_required
def administrative_entities_geojson(request, administrative_entity_id):

    administrative_entity = models.PermitAdministrativeEntity.objects.filter(id=administrative_entity_id)

    geojson = json.loads(serialize('geojson', administrative_entity,
                                   geometry_field='geom',
                                   srid=2056,
                                   fields=('id', 'name', 'ofs_id', 'link',)))

    return JsonResponse(geojson, safe=False)


# ///////////////////////////////////
# DJANGO REST API
# ///////////////////////////////////


class GeocityViewConfigViewSet(viewsets.ViewSet):

    def list(self, request):

        config = {'meta_types': dict((str(x), y) for x, y in models.WorksType.META_TYPE_CHOICES)}

        config['map_config'] = {
            'wmts_capabilities': settings.WMTS_GETCAP,
            'wmts_layer': settings.WMTS_LAYER,
            'wmts_capabilities_alternative': settings.WMTS_GETCAP_ALTERNATIVE,
            'wmts_layer_aternative': settings.WMTS_LAYER_ALTERNATIVE,
        }

        geojson = json.loads(serialize('geojson', models.PermitAdministrativeEntity.objects.all(),
                                       geometry_field='geom',
                                       srid=2056,
                                       fields=('id', 'name', 'ofs_id', 'link',)))

        config['administrative_entities'] = geojson

        return JsonResponse(config, safe=False)


class PermitRequestGeoTimeViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = serializers.PermitRequestGeoTimeSerializer

    def get_queryset(self):
        """
        This view should return a list of events for which the loggued user has
        view permissions
        """
        user = self.request.user
        starts_at = self.request.query_params.get('starts_at', None)
        ends_at = self.request.query_params.get('ends_at', None)
        administrative_entity = self.request.query_params.get('adminentity', None)

        base_filter = Q()
        if starts_at:
            start = datetime.datetime.strptime(starts_at, '%Y-%m-%d')
            base_filter &= (Q(starts_at__gte=start))
        if ends_at:
            end = datetime.datetime.strptime(ends_at, '%Y-%m-%d')
            base_filter &= Q(ends_at__lte=end)
        if administrative_entity:
            base_filter &= Q(permit_request__administrative_entity=administrative_entity)

        works_object_types_prefetch = Prefetch("permit_request__works_object_types",
                                               queryset=models.WorksObjectType.objects.select_related("works_type"))

        qs = models.PermitRequestGeoTime.objects.filter(base_filter).filter(
                 Q(permit_request__in=services.get_permit_requests_list_for_user(user)) |
                 Q(permit_request__is_public=True)).prefetch_related(
                    works_object_types_prefetch).select_related("permit_request__administrative_entity")

        return qs.order_by('starts_at')
