from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from .models import OrdemServico, HistoricoManutencao
from .serializers import OrdemServicoSerializer, HistoricoManutencaoSerializer

class OrdemServicoViewSet(viewsets.ModelViewSet):
    queryset = OrdemServico.objects.all()
    serializer_class = OrdemServicoSerializer
    
    # Adicionando os filtros de nível Sênior
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    
    # Filtros exatos: Perfeito para botões de filtro na tela
    filterset_fields = ['status', 'prioridade', 'equipamento', 'responsavel']
    
    # Busca por texto: Perfeito para a barra de pesquisa
    search_fields = ['titulo', 'descricao']

class HistoricoManutencaoViewSet(viewsets.ModelViewSet):
    queryset = HistoricoManutencao.objects.all()
    serializer_class = HistoricoManutencaoSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['ordem_servico', 'data_execucao']
    search_fields = ['descricao_servico']