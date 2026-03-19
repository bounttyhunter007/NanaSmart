from rest_framework import viewsets, filters # Importamos o filters do DRF
from django_filters.rest_framework import DjangoFilterBackend # Importamos o backend de filtros
from .models import Empresa, Usuario
from .serializers import EmpresaSerializer, UsuarioSerializer

class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    
    # Podemos colocar filtros nas empresas também!
    filter_backends = [filters.SearchFilter]
    search_fields = ['nome', 'cnpj'] # Permite buscar empresa por nome ou CNPJ

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    
    # ATIVANDO OS FILTROS E BUSCAS
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    
    # 1. Filtros Exatos (Filter)
    filterset_fields = ['empresa', 'tipo_usuario', 'cargo']
    
    # 2. Busca por Texto (Search)
    search_fields = ['first_name', 'last_name', 'email', 'username']