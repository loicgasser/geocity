import os
import datetime
from weasyprint import HTML, CSS
import urllib.parse
from django.shortcuts import render
from django.conf import settings
from . import services, models
import base64
import requests
from django.contrib.gis.db.models import Extent
from django.core.files.base import ContentFile


def get_map_base64(geo_times, permit_id):

    extent = list(geo_times.aggregate(Extent('geom'))['geom__extent'])
    buffer_extent = int(os.environ["PRINT_MAP_BUFFER_METERS"])
    h_extent_left = round(extent[0] - buffer_extent)
    h_extent_right = round(extent[2] + buffer_extent)
    v_extent_scaled = round((extent[2] - extent[0]) * (1800/2500))
    v_extent_bottom = round(extent[1] - buffer_extent)
    v_extent_top = round(v_extent_bottom + v_extent_scaled + buffer_extent)
    extent = [h_extent_left, v_extent_bottom, h_extent_right, v_extent_top]

    layers = 'permit_permitrequestgeotime_polygons,permit_permitrequestgeotime_lines,permit_permitrequestgeotime_points'

    values = {'SERVICE': 'WMS',
              'VERSION': '1.3.0',
              'REQUEST': 'GetPrint',
              'FORMAT': 'png',
              'TRANSPARENT': 'true',
              'SRS': 'EPSG:2056',
              'DPI': '150',
              'TEMPLATE': 'permits',
              'map0:extent': ', '.join(map(str, extent)),
              'LAYERS': settings.PRINTED_REPORT_LAYERS + layers,
              'FILTER': 'gpf_permitrequest:"id" >= ' + str(permit_id)
              + ' AND "id" < ' + str(permit_id + 1),
              }

    data = urllib.parse.urlencode(values)
    printurl = "http://qgisserver" + '/?' + data
    response = requests.get(printurl)
    map_base64 = ("data:" +
                  response.headers['Content-Type'] + ";" +
                  "base64," + base64.b64encode(response.content).decode("utf-8"))

    return map_base64


def printreport(request, permit_request):

    geo_times = permit_request.geo_time.all()
    map_image = get_map_base64(geo_times, permit_request.pk)
    print_date = datetime.datetime.now()
    validations = permit_request.validations.all()
    objects_infos = services.get_permit_objects(permit_request)
    actor_types = dict(models.ACTOR_TYPE_CHOICES)

    contacts = [
        (actor_types.get(contact['actor_type'].value(), ''), [
            (field.label, field.value())
            for field in contact
            if field.name not in {'id', 'actor_type'}
        ])
        for contact in services.get_permitactorformset_initiated(permit_request)
        if contact['id'].value()
    ]

    author = permit_request.author
    administrative_entity = permit_request.administrative_entity

    html = render(request, "permits/print/printpermit.html", {
        'permit_request': permit_request,
        'contacts': contacts,
        'author': author,
        'objects_infos': objects_infos,
        'print_date': print_date,
        'administrative_entity': administrative_entity,
        'geo_times': geo_times,
        'map_image': map_image,
        'validations': validations,
        'logo_main': base64.b64encode(administrative_entity.logo_main.open().read()).decode("utf-8") if administrative_entity.logo_main else '',
        'logo_secondary': base64.b64encode(administrative_entity.logo_secondary.open().read()).decode("utf-8") if administrative_entity.logo_secondary else '',
        'image_signature_1': base64.b64encode(administrative_entity.image_signature_1.open().read()).decode("utf-8") if administrative_entity.image_signature_1 else '',
        'image_signature_2': base64.b64encode(administrative_entity.image_signature_2.open().read()).decode("utf-8") if administrative_entity.image_signature_2 else '',
    })

    pdf_permit = HTML(string=html.content,  base_url=request.build_absolute_uri()).write_pdf(
        stylesheets=[CSS('/code/static/css/printpermit.css')])

    file_name = 'permis_' + str(permit_request.pk) + '.pdf'
    permit_request.printed_file.save(file_name, ContentFile(pdf_permit), True)
    permit_request.printed_at = datetime.datetime.now()
    permit_request.printed_by = request.user.get_full_name()
    permit_request.save()

    return pdf_permit
