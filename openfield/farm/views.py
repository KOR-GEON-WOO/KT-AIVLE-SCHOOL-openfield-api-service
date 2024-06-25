from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from .models import FarmStatusLog
from .serializers import FarmStatusLogSerializer

class FarmStatusLogListView(generics.ListAPIView):
    serializer_class = FarmStatusLogSerializer
    pagination_class = PageNumberPagination
    pagination_class.page_size = 10  # 페이지당 보여줄 항목 수 설정

    def get_queryset(self):
        farm_created = self.request.query_params.get('farm_created', None)
        if farm_created:
            queryset = FarmStatusLog.objects.filter(farm_created=farm_created)
        else:
            queryset = FarmStatusLog.objects.all()
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.serializer_class(page, many=True)
            data = [
                {
                    'farm_id': item.farm.farm_id,
                    'farm_owner': item.farm.farm_owner,
                    'latitude': item.farm.latitude,
                    'longitude': item.farm.longitude
                }
                for item in serializer.data
            ]
            return self.get_paginated_response(data)

        serializer = self.serializer_class(queryset, many=True)
        data = [
            {
                'farm_id': item.farm.farm_id,
                'farm_owner': item.farm.farm_owner,
                'latitude': item.farm.latitude,
                'longitude': item.farm.longitude
            }
            for item in serializer.data
        ]
        return Response(data)

class FarmStatusLogDetailView(generics.RetrieveAPIView):
    queryset = FarmStatusLog.objects.all()
    serializer_class = FarmStatusLogSerializer
