# Criticidade de equipamentos e priorização de OS

A regra atual é ABC para equipamento e OS, com classe herdada uma única vez na abertura, critérios validados por empresa e ajuste explícito de gestor/admin com justificativa.

A implementação anterior A/B/C/D com matriz de gravidade foi substituída. Consulte [Priorização ABC](../PRIORIZACAO_ABC.md) para os critérios, fluxo de uso, interfaces, migrações, permissões e testes atualizados.

`PrioridadeOSService` continua sendo o serviço de entrada usado por alertas e planos. A herança também é garantida na criação do modelo para contemplar comandos e administração. As consultas compartilham a precedência ABC no servidor; a interface não reordena apenas uma página.

As revisões de critérios e os históricos de criticidade/prioridade preservam as decisões anteriores. Não se preenche o contexto da abertura de ordens legadas com a avaliação atual do equipamento.
