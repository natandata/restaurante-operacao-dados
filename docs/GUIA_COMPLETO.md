# Restaurante: código e decisões

Documento aprofundado da implementação independente · versão de estudo · novembro de 2026

Este documento acompanha uma implementação assistida por IA. A publicação no GitHub ainda depende de revisão.

## O que foi construído

Uma plataforma independente de estudo para acompanhar a operação de um restaurante fictício, do evento ao indicador.

### O resultado

O projeto tem dois contextos deliberadamente separados. A operação ao vivo guarda pedidos, reservas, consumo e recebimentos em SQLite. A análise histórica parte de um ano de dados sintéticos, valida arquivos CSV, carrega DuckDB e usa dbt para construir dimensões, fatos e tabelas de indicadores. React apresenta a operação e as análises; Streamlit oferece um painel histórico complementar. A previsão compara quatro métodos e produz sete dias após o fim do histórico. Nenhum dado é de um restaurante real.

### Como ler

Para rodar: leia Ambiente e execução. Para entender uma venda: leia Domínio, Transações e API. Para explicar o caminho até um gráfico: leia Gerador, Ingestão, Warehouse e Indicadores. Para uma entrevista: leia Decisões e limites e depois execute o roteiro de demonstração. O apêndice de cada capítulo abre os arquivos reais da implementação. Não há trechos ilustrativos fingindo ser o código que foi testado.

### O que “completo” significa aqui

Todos os blocos pedidos existem como demonstração executável: dados, importação, SQL, análise, previsão, serviço, atualização ao vivo, interfaces, testes e documentação. Completo não significa pronto para produção. Não há autenticação, permissões por pessoa, integração com pagamentos ou fornecedores, nota fiscal, deploy público ou conexão com um restaurante. O GitHub continua sujeito à revisão de nome, README, conteúdo e audiência.

### Autoria sem disfarce

A implementação foi escrita de forma independente com assistência de IA para Natan estudar e modificar. O código, os dados, os textos e as telas do repositório inicialmente citado não foram reutilizados. Isso não transforma trabalho assistido em trabalho feito sozinho e não elimina licenças de bibliotecas ou da fonte Inter. O nome do produto ainda é provisório. Não há alegação de implantação em cliente ou melhoria comercial.

### Evidência medida

A verificação local inclui 37 testes Python, 7 testes de funções da interface, construção TypeScript/Vite e 63 etapas dbt: 31 modelos (20 tabelas e 11 views) e 32 testes de dados. A demonstração anual gerou 151.447 linhas em 11 tabelas CSV, com 30.826 pedidos. Esses números descrevem esta execução e esta configuração; não são garantias para qualquer alteração futura.

### Arquivos para estudar

- `README.md`

## Arquitetura e responsabilidades

Separar evento operacional e consulta histórica evita que uma tela analítica se torne a dona do estoque.

### Camadas

operacao/settings.py define caminhos e o catálogo fictício; domain.py preserva o primeiro exercício em memória. store.py implementa a operação persistente. synthetic.py cria o histórico. ingestion.py valida e importa. warehouse/ contém o grafo dbt. forecast.py treina e avalia. api.py apresenta contratos HTTP e WebSocket. frontend/ contém a interface; app/Home.py é o painel histórico. scripts/prepare.py coordena a preparação de dados.

### Fluxo histórico

Configuração e semente → CSVs sintéticos → validação do lote → schema raw no DuckDB → views stg → cálculo intermediário de valor do pedido → dimensões e fatos → sete marts → API/React ou Streamlit. A staging atual é uma view que preserva as colunas, não um mecanismo de correção automática. Tipos de datas e nomes analíticos são definidos nos modelos seguintes. Não confundir uma camada com uma limpeza que ela não faz.

### Fluxo operacional

Um comando HTTP entra no Store, abre transação SQLite com BEGIN IMMEDIATE, verifica repetição, valida a regra, muda pedidos e movimentos, registra evento e salva a resposta do comando. A transação termina antes de o cliente receber sucesso. A interface consulta o estado e recebe aviso de novos eventos pelo WebSocket. Não há escrita de estoque diretamente pelo React.

### Por que dois bancos

SQLite é usado para pequenas transações locais e persistência do estado de demonstração. DuckDB é usado para leituras analíticas e transformações de um lote maior. O benefício é deixar o papel de cada um claro. A limitação é que o histórico não inclui automaticamente os pedidos ao vivo: isso está escrito nas telas. Uma próxima evolução poderia extrair eventos do SQLite para uma raw incremental, mantendo cursor e reconciliação. Essa ponte não é fingida nesta versão.

### Escala e implantação

A API deve escutar apenas 127.0.0.1. O simulador é um processo assíncrono local, não um sistema distribuído. Rodar múltiplos workers criaria múltiplos simuladores independentes; não faça isso nesta versão. As credenciais de contas do usuário não fazem parte do projeto. A preparação pode baixar bibliotecas, mas não cria serviços pagos.

### Arquivos para estudar

- `operacao/settings.py`
- `scripts/prepare.py`

## Domínio, dinheiro e unidades

Uma regra só fica clara quando é possível calcular um caso sem executar o programa.

### Entidades

Produtos possuem código, nome, categoria, preço e custo ilustrativo. Uma receita liga o produto ao ingrediente e à quantidade na unidade-base. Ingredientes têm uma unidade única, saldo inicial e limite de alerta. Pedidos ligam itens, canal, horários e estado. Movimentos separam alteração física de reserva. Recebimentos precisam de aprovação. Eventos ordenam mudanças; commands guardam a chave, o conteúdo e a resposta de um comando aceito.

### Precisão monetária

O valor de R$26,00 é guardado como 2600 centavos. No domínio transacional, total é preço inteiro vezes quantidade inteira. Não há soma de floats para o dinheiro do pedido. O histórico usa taxas ilustrativas com arredondamento para centavos. Isso simplifica a demonstração, mas não implementa regras fiscais, arredondamento de uma nota ou cálculo contábil. O campo unit_cost_cents do recebimento é por unidade-base, o que exige atenção: custo por grama não é custo por quilo.

### Exemplo de reserva

O prato P01 usa 160g de arroz e 140g de feijão. Dois pratos reservam 320g e 280g. Se o arroz físico for 25.000g, continua nesse valor na reserva; o reservado passa a 320g e o disponível a 24.680g. Começar o preparo reduz o físico em 320g e libera a reserva de 320g. Cancelar antes do preparo libera a reserva sem mudar o físico.

### Máquina de estados

reservado pode virar preparando ou cancelado. preparando pode virar concluido. Concluído e cancelado não têm próximas transições. Nesta versão, não se cancela depois de iniciar preparo, porque seria necessário decidir perda, reaproveitamento e devolução por ingrediente. O serviço rejeita esse atalho em vez de devolver estoque consumido sem critério.

### A primeira versão e a evolução

domain.py é o módulo introdutório sem dependências: vender consome imediatamente e guarda estado em memória. O serviço real desta versão usa store.py: primeiro reserva, depois consome. O exercício antigo não é o motor da API. Entender essa diferença evita explicar uma regra antiga ao demonstrar a nova aplicação.

### Arquivos para estudar

- `operacao/domain.py`
- `operacao/settings.py`

## Transações e trilha de eventos

Uma operação com falha não pode deixar meio pedido consumido.

### Tudo ou nada

Store.connection(write=True) abre BEGIN IMMEDIATE. Isso serializa escritores locais durante a validação e a escrita. O pedido só é inserido se todos os produtos existirem, as quantidades forem inteiras positivas, o limite por produto for respeitado e todos os ingredientes estiverem disponíveis. Se qualquer etapa lançar exceção, rollback desfaz o bloco. A regra é do pedido inteiro, não aceitar silenciosamente só parte dele.

### Idempotência

O cliente envia uma key. O servidor serializa o conteúdo do comando de forma estável e procura essa chave em commands. Se a chave já existe com o mesmo conteúdo, devolve a resposta anterior sem consumir de novo. Se existe com outro conteúdo, responde conflito. Uma chave diferente não autoriza reutilizar um pedido ou recebimento já existente. Esse mecanismo lida com uma repetição controlada; a interface atual gera uma chave nova por clique, então não existe promessa de recuperação perfeita de um clique cujo resultado se perdeu na rede.

### Movimentos, não edição muda

Cada reserva cria movimento com physical_delta=0 e reserved_delta positivo. Preparo cria physical_delta negativo e reserved_delta negativo. Cancelamento de reserva só reduz reserved_delta. Recebimento aprovado cria physical_delta positivo. O saldo resulta do saldo inicial mais a soma dos movimentos. Essa trilha permite explicar a alteração, em vez de olhar apenas um número final sem origem.

### Recebimento em dois passos

receive registra pendente e não aumenta saldo. approve exige que ainda esteja pendente, registra a entrada e altera o estado para aprovado na mesma transação. Repetir o comando com a mesma chave devolve a resposta; tentar nova aprovação com outra chave gera conflito. A tela pede confirmação. Não existe compra, cobrança, comunicação com fornecedor ou conferência de nota fiscal real.

### Persistência e limites

O banco é arquivo local. Reiniciar a API preserva pedidos, movimentos, eventos e chaves. A flag de simulador e seu contador de rejeições não são persistidos. Estado HTTP mostra até 500 pedidos/recebimentos recentes; os totais consultam todo o banco, e isso aparece na tela. Não há retenção automática, backup automático, migração de schema ou autenticação nesta versão.

### Arquivos para estudar

- `operacao/store.py`

## Gerador de dados sintéticos

Dados sintéticos precisam contar uma história verificável, não parecer uma extração de cliente.

### Reprodutibilidade

generate recebe dias, semente, data inicial e volume médio diário. A sequência pseudoaleatória é local à execução e não depende de uma conta ou fonte externa. O mesmo conjunto de parâmetros produz os mesmos arquivos. A função recusa destino não vazio para não substituir um cenário que o usuário esteja estudando. O manifest.json registra a configuração e a contagem de linhas.

### Pedido e contexto

O volume diário usa multiplicador por dia da semana, promoção simulada, chuva simulada e variação aleatória. Temperatura vem de uma forma sazonal simples com ruído. Essas relações foram escolhidas para este exercício e não estimadas de um restaurante. Cada pedido recebe canal, horário, produtos, quantidades e tempos. Custos e taxas são hipóteses ilustrativas. Não há feriados oficiais ou previsão de tempo real por trás do conjunto.

### Estoque com falha possível

Recebimentos reabastecem ingredientes em dias em que o saldo está abaixo do gatilho e a entrega simulada acontece. Um pedido que demanda mais do que existe é cancelado por sem_ingrediente. Outro pequeno grupo cancela por desistência. Pedidos concluídos consomem receita; perdas diárias reduzem uma fração pequena do saldo. Não há saldo negativo deliberado no gerador. Isso permite estudar falta sem afirmar que a operação sempre consegue comprar emergencialmente.

### Equipe e avaliações

A escala tem pessoas identificadas por códigos, funções e custos inventados. Presença é sorteada; o tempo de preparo depende de volume e equipe disponível. Avaliações são notas calculadas a partir do preparo e ruído. Não existem nomes de clientes, textos coletados, salários reais, CNPJ, contatos ou menu copiado. Mesmo uma relação plausível entre atraso e nota é uma regra do gerador, não uma descoberta científica.

### Como mudar com critério

Mude um parâmetro por vez e gere em outra pasta. Compare taxas de cancelamento, saldo e preparo, não só a quantidade de linhas. Antes de aumentar volume para um milhão de pedidos, estime tempo, disco e memória. Não use o número de linhas como sinônimo de qualidade. O conjunto anual desta execução tem 365 dias, 30.826 pedidos, 46.287 itens, 2.555 turnos, 7.091 avaliações e 63.563 movimentos.

### Arquivos para estudar

- `operacao/synthetic.py`

## Ingestão, rejeição e auditoria

Um lote inválido precisa falhar de forma visível sem contaminar o que já estava carregado.

### Contrato de arquivos

TABLES e REQUIRED declaram os onze arquivos e colunas esperadas. O importador lê CSVs, recusa tabela vazia, valida identificadores, datas, números finitos, inteiros quando exigidos e valores negativos em contextos proibidos. Movimento admite quantidade negativa por representar saída. Quantidade de item de venda não admite zero. Não existe inferência silenciosa de uma coluna que faltou.

### Relações e reconciliação

Itens precisam apontar para pedido e produto conhecidos; avaliações apontam para pedidos; turnos para equipe; movimentos e recebimentos para ingredientes; recebimentos para fornecedor. Notas ficam entre um e cinco. O pedido concluído deve ter receita líquida igual a bruto menos desconto e taxa. A soma do bruto dos itens deve bater com o bruto do pedido. Esses testes impedem que um join plausível esconda uma linha perdida.

### Rejeição de lote

Qualquer erro gera rejections.json ao lado dos arquivos e lança BatchRejected. O banco histórico não recebe uma parte boa do mesmo lote. Esse desenho é simples e seguro para um cenário de estudo. Para ingestão real, seria necessário decidir política de quarentena por linha, reprocessamento, versionamento de contrato e autorização para dados pessoais. Não existe garantia de validação universal de qualquer CSV arbitrário.

### Atomicidade no DuckDB

Depois da validação, o importador calcula um hash do conteúdo e abre uma transação. Cada raw é substituída pelo lote validado. Se uma escrita falhar, rollback preserva o estado anterior. O registro de auditoria contém hash, horário e total de linhas. O projeto não soma o mesmo lote em raw indefinidamente: raw representa um snapshot do lote, e os marts são reconstruídos.

### Mudança de lote

A importação repetida do snapshot atual retorna duplicate. audit.current_snapshot guarda o hash ativo. Se um lote A foi seguido de B, reimportar A deve carregar A outra vez, e não tratá-lo como duplicado só porque apareceu na auditoria. Há teste para A → B → A. Os CSVs anteriores precisam existir para essa restauração, e os marts precisam ser reconstruídos. A auditoria de hashes não armazena sozinha todos os conteúdos antigos. O teste de lote inválido verifica que o total da raw não muda depois da rejeição.

### Arquivos para estudar

- `operacao/ingestion.py`

## Warehouse e grafo dbt

O grão de cada tabela decide que soma faz sentido.

### O grafo atual

Onze stg_ views preservam as raw validadas. int_order_value centraliza a conta de receita do pedido. Seis dimensões descrevem produto, data, ingrediente, pessoa da equipe, fornecedor e canal. Seis fatos descrevem pedido, item, turno, avaliação, movimento e recebimento. Sete marts agregam perguntas operacionais. A construção local atual tem 31 modelos e 32 checagens de dados.

### Dimensões e fatos

fact_order tem uma linha por pedido. fact_item tem uma linha por produto dentro de um pedido no gerador atual, mas não tem identificador de item independente. fact_shift tem uma linha por pessoa/dia. fact_review tem uma linha por avaliação. fact_movement registra uma mudança de ingrediente com data e origem. Fazer join de pedidos com itens e somar novamente a receita do pedido duplica valores; use o grão correto, ou agregue itens antes.

### O que dbt faz

ref define dependências entre modelos. source aponta para raw. dbt constrói a ordem correta e executa testes de unicidade/nulidade e testes SQL de reconciliação. A transformação não chama serviço de IA. As tabelas e views são locais no DuckDB. Rodar da raiz importa porque profiles.yml aponta por padrão para data/restaurant.duckdb. O caminho pode ser definido por RESTAURANTE_WAREHOUSE.

### Não exagerar a camada staging

As views staging desta implementação não corrigem texto nem fazem dezenas de casts. Esse é um recorte explícito: o lote já vem com contrato validado e dimensões/fatos dão nomes e datas analíticas. A camada permite uma futura fonte diferente sem mudar todos os consumidores, mas isso só terá valor se ela passar a normalizar fontes diferentes. Não descrever essa intenção como integração já existente.

### Um indicador até a origem

Para explicar receita líquida por dia, comece em mart_daily: ele junta dim_date e fact_order, agrupa no dia e soma net_cents. fact_order deriva de int_order_value, que deriva de stg_orders; a view aponta raw.orders. O CSV orders.csv foi gerado pelo synthetic.py, e ingestion.py verificou os valores antes de escrever raw. Esse caminho é rastreável no código, não depende de acreditar num screenshot.

### Arquivos para estudar

- `warehouse/models/fact_order.sql`
- `warehouse/models/fact_item.sql`
- `warehouse/models/mart_daily.sql`
- `warehouse/models/mart_inventory.sql`
- `warehouse/models/schema.yml`

## Análises e interpretação

Uma tela só ajuda quando o nome do indicador não promete mais do que a conta entrega.

### Visão diária

orders conta todos os pedidos; completed e cancelled separam os estados. net_cents é receita após descontos e taxas no pedido concluído. contribution_cents subtrai custo ilustrativo de alimento. Isso não é lucro líquido: faltam tributos, aluguel, energia, depreciação e outras despesas. O filtro de datas da tela React se aplica à série e aos três cartões diários, não aos quadros globais abaixo. Essa fronteira é escrita na interface.

### Cardápio e canais

mart_menu resume unidades, bruto e margem antes de desconto/taxa por produto vendido em pedido concluído. Não aloca desconto do pedido entre produtos, então o rótulo evita chamar essa conta de lucro do produto. mart_channel soma líquido, taxa e contribuição de pedidos concluídos por canal. Taxas são premissas do cenário, não contratos de plataformas reais.

### Atendimento e equipe

mart_service calcula contagem e média de preparo por dia/canal e número de pedidos acima da promessa. A tela React calcula média ponderada pelas contagens ao resumir o histórico. mart_labour compara pedidos concluídos, horas e custo da equipe por dia; contribuição após trabalho ainda não é lucro líquido. Pessoas são fictícias, e produtividade simulada não serve para avaliar trabalhadores reais.

### Estoque e experiência

mart_inventory é um saldo final do conjunto anual, com consumo e perda por ingrediente. Não é tendência diária nem estoque ao vivo. Misturar gramas e mililitros numa soma geral não tem sentido; por isso a unidade acompanha o ingrediente. mart_experience agrega notas e contagem por dia/categoria. Poucas avaliações não justificam conclusão forte, e todas as notas foram geradas por regra.

### Estados vazios e erros

Ausência de resposta do serviço não pode aparecer como zero de vendas. A interface diferencia carregamento, erro, filtro sem linhas e tabela vazia. Dados anteriores podem ficar visíveis em falha, acompanhados do aviso de que podem estar desatualizados. A revisão visual e funcional inclui filtro sem resultado e botão de limpar. Essa distinção vale tanto quanto a estética do gráfico.

### Arquivos para estudar

- `warehouse/models/mart_menu.sql`
- `warehouse/models/mart_channel.sql`
- `warehouse/models/mart_service.sql`
- `warehouse/models/mart_labour.sql`
- `warehouse/models/mart_experience.sql`
- `app/Home.py`

## Previsão sem vazamento temporal

O teste mede uma escolha já feita; não participa da escolha.

### A pergunta

Prever o volume diário total de pedidos do cenário. Há quatro candidatos: repetir a semana anterior; média dos sete dias anteriores; Ridge; floresta aleatória com semente fixa. FEATURES contém dia da semana, mês, lag7 e média dos sete dias anteriores. O pedido do dia-alvo não entra no próprio lag nem na média: shift(1) vem antes de rolling(7).

### Partição cronológica

Depois de remover os sete primeiros dias sem histórico suficiente, 65% vão para treino, a faixa até 82% para validação, e o restante para teste. Nesta execução: 232 dias de treino, 61 de validação e 65 de teste. O candidato com menor MAE na validação é escolhido. Depois se ajustam os candidatos com treino+validação e se medem no teste. A escolha não é refeita olhando o menor erro de teste.

### O que a avaliação mede

O teste é de um dia à frente com histórico anterior observado disponível. Isso significa que as features de um dia posterior do teste podem usar a demanda realmente observada em dias anteriores do teste. Não é vazamento do futuro para o próprio dia, mas também não é uma previsão congelada de todos os 65 dias de uma vez. A previsão futura de sete dias é diferente: ela usa as próprias previsões anteriores para atualizar lags e médias.

### Métricas

MAE é a média do erro absoluto em pedidos. RMSE calcula a raiz da média do erro quadrático e penaliza desvios maiores. WAPE é a soma do erro absoluto dividida pela soma da demanda absoluta; retorna ausência quando o denominador é zero. Não é uma acurácia de classificação nem taxa de ganho comercial. A tabela guarda métricas de cada modelo e separa validação de teste.

### Resultado desta execução

semana_anterior: MAE validação 9.54; MAE teste 13.78; RMSE teste 18.04; WAPE teste 16.22%.
media_sete_dias: MAE validação 12.41; MAE teste 16.24; RMSE teste 21.02; WAPE teste 19.11%.
ridge: MAE validação 8.64; MAE teste 10.92; RMSE teste 15.12; WAPE teste 12.84%.
floresta: MAE validação 8.06; MAE teste 10.95; RMSE teste 14.17; WAPE teste 12.88%.
Modelo escolhido: floresta. Não transportar esses números para outra semente ou dados reais.

### Futuro e equipe

Depois da avaliação, o modelo escolhido é reajustado com todo o histórico e prevê sete dias recursivamente. A data futura é relativa ao último dia do dataset. Não é automaticamente a semana de hoje. A sugestão de pessoas usa pedidos previstos divididos pela mediana histórica de pedidos por hora de cozinha vezes oito horas, arredondando para cima. Não considera lei trabalhista, disponibilidade individual, intervalos, habilidades ou otimização de escala.

### Limites

Não há intervalo probabilístico calibrado. Um único corte temporal não mostra estabilidade em todas as épocas; uma evolução adequada é backtest com múltiplas janelas, mantendo um teste final intocado. Dados do mesmo gerador podem facilitar a previsão. Bom erro aqui demonstra o mecanismo, não prova generalização no mundo real. O sistema não toma decisão sobre funcionários automaticamente.

### Arquivos para estudar

- `operacao/forecast.py`

## API, contratos e erros

Contratos pequenos tornam as regras de negócio observáveis sem expor o banco à interface.

### Leituras

GET /api/health informa serviço e existência do warehouse. /api/catalogue devolve produtos. /api/state devolve pedidos recentes, estoque, recebimentos, cursor e totais. /api/events?after=N recupera até 500 eventos após uma sequência. /api/analytics/{name} aceita somente nomes de marts previstos no mapa, sem SQL arbitrário enviado pelo usuário. /api/forecast lê o resultado calculado previamente.

### Escritas

POST /api/orders recebe key, id, items e channel. POST /api/orders/{id}/transition recebe key e target. /api/receipts recebe o recebimento pendente; /api/receipts/{id}/approve registra a aprovação. /api/simulator/start ou stop muda apenas a simulação desta execução. A validação Pydantic usa StrictInt para não aceitar True como quantidade um. Isso importa em Python porque bool é uma subclasse de int.

### Semântica de erro

Conflitos de regra retornam 409 com explicação, como ingrediente insuficiente, pedido já existente, transição impossível ou chave reutilizada com conteúdo diferente. Payload que não corresponde ao schema pode retornar 422. Uma origem não permitida em escrita retorna 403. Erro não é convertido em resposta de sucesso com saldo zero. Os testes exercitam comandos válidos e inválidos pelo cliente HTTP real do framework.

### Origens e uso local

CORS permite somente as origens locais listadas. As escritas verificam Origin quando presente; WebSocket verifica origem antes de aceitar. Isso reduz risco de outra página no navegador acionar a demonstração, mas não substitui autenticação. Um cliente local sem Origin ainda pode chamar a API. Vincular em 0.0.0.0 ou colocar atrás de um domínio público sem redesenhar segurança está fora desta entrega.

### O que não existe

Não há fila externa, autenticação, autorização por papel, TLS próprio, rate limiting de produção, proteção contra todos os tipos de abuso, migração de banco, trilha legal de aprovação, aprovação de compra ou nota fiscal. O OpenAPI do FastAPI serve para inspecionar contratos localmente em /docs. Não publicar essa documentação com dados do usuário nem tratá-la como contrato de produto comercial.

### Arquivos para estudar

- `operacao/api.py`

## WebSocket, reconexão e simulador

Evento novo e estado completo têm funções diferentes.

### Sequência persistente

Cada mudança aceita grava um evento com seq crescente, horário UTC, tipo e payload. O WebSocket envia um snapshot ao conectar e depois eventos após o cursor informado. O cliente mantém o maior seq já observado. Eventos que chegam fora de ordem não fazem o cursor regredir. A interface atual usa eventos como sinal para reler estado, em vez de aplicar movimentos de estoque no navegador.

### Reconexão

Quando a conexão fecha, o cliente tenta de novo com espera exponencial limitada a quinze segundos. O cursor é enviado em after. O servidor pode devolver até 500 eventos por consulta e continuar nas próximas passagens. Snapshot reconstrói o estado recente mesmo se o cliente ficou longe por algum tempo. O cursor fica em memória do componente, não em armazenamento durável do navegador; recarregar a página pode reler eventos antigos, mas não reexecuta comandos de escrita.

### Batimento e sessão

Sem eventos novos, o serviço envia heartbeat. Isso mantém a conexão viva e permite distinguir canal ativo de uma tela estática. O contador seq pertence ao banco de eventos e sobrevive ao processo; a flag de simulador não. O serviço não considera o navegador a fonte de verdade do estoque. A consulta HTTP continua útil se o fluxo de eventos estiver se reconectando.

### Simulação explícita

O usuário precisa clicar iniciar. A cada três segundos, o processo tenta um pedido fictício, reserva, inicia preparo e conclui. Estoque insuficiente incrementa rejeições da execução sem saldo negativo. Não recebe mercadoria automaticamente. A simulação não é a mesma distribuição temporal do conjunto anual: é uma ferramenta curta para demonstrar eventos e falhas. Não representa tráfego real de restaurante.

### Teste e limite

Os testes de API conectam em /ws, verificam snapshot, replay e heartbeat. Testes de funções da interface verificam cursor monotônico. A revisão de navegador exercita os botões de iniciar e pausar e observa a atualização. Ainda não é um teste de carga com milhares de clientes, perda de rede real ou múltiplos servidores. Antes de ampliar escala seria necessário tratar broadcast, fila, backpressure, autenticação e retenção de eventos.

### Arquivos para estudar

- `frontend/src/lib.ts`

## Interface e marca

As áreas acompanham o trabalho, não repetem as páginas de um repositório de referência.

### Seis áreas

Hoje reúne fila, pedido manual e simulador; Investigar reúne a série diária e os temas de negócio; Abastecer diferencia físico, reservado e disponível e exige segundo passo no recebimento; Planejar mostra comparação e futuro; Conferir dados explica origem e separação de contextos; Sobre documenta decisões e limites. A navegação e as telas são próprias. Streamlit preserva uma leitura analítica complementar em oito áreas.

### Identidade vigente

A marca usa o manual de novembro com Inter, não o manual antigo com fonte pixel. Azul #3f3cd8, fundo #fbfbfa, superfícies brancas, texto #161514, apoio #5c5955, linhas #e9e8e4 e pontos #e3e2dc. Títulos pesados com tracking apertado; cards de 18px; botões em pílula; sem gradiente ou sombra pesada. A assinatura tipográfica é data with natan em minúsculas. Não recortamos um logo ilustrativo do PDF como asset oficial.

### Adaptação operacional

A aplicação não é uma landing page. Tabelas e valores têm prioridade sobre decoração; as áreas de ação têm foco claro. A tela informa unidade de ingrediente e separação de histórico/ao vivo. Gráfico diário dá uma leitura de ritmo, mas o indicador em texto e os dados de origem continuam disponíveis. Navegação no telefone permite deslocamento horizontal; tabelas são conteúdo largo complementar e mantêm rolagem contida.

### Português e inglês

O controle PT/EN troca os textos públicos da interface React, estados e nomes do cenário. Identificadores de API e nomes técnicos podem permanecer no contrato original. Erros detalhados retornados pelo backend ainda podem aparecer em português; essa é uma limitação de localização operacional, não conteúdo de marketing oculto. As duas versões foram capturadas em 320, 390 e 1280px. Datas de cenário e dinheiro preservam o mesmo significado.

### Revisão visual real

As capturas foram feitas com a aplicação rodando e dados carregados, não maquetes. A primeira revisão encontrou moeda quebrando em cartões estreitos e uma captura de análise antes da chegada dos dados. Corrigimos o empilhamento de cartões no telefone e a espera por dados antes de capturar. A revisão também conferiu que os números não são apresentados como ganho comercial e que os botões de recebimento executam o fluxo esperado.

### Arquivos para estudar

- `frontend/src/App.tsx`
- `frontend/src/style.css`
- `ui/brand-tokens.css`

## Testes e critérios de aceite

Passar em teste não dispensa a inspeção da tela nem transforma uma demonstração em produto.

### Camada Python

O conjunto atual tem 37 testes, incluindo o módulo inicial, regras de reserva, consumo, cancelamento, idempotência, persistência, concorrência, aprovação de recebimento, validação HTTP, bloqueio de origem indevida, WebSocket, geração reproduzível, rejeição de lote e pipeline com previsão. Há também subcasos parametrizados. A execução mede o código atual, não uma promessa de cobertura total.

### Dados e frontend

dbt constrói 31 modelos e executa 32 testes de dados. Eles cobrem unicidade/nulidade em chaves e reconciliações específicas; não são 63 testes unitários. Vitest executa sete testes de funções de apresentação, moeda, cursor e rótulos. O build TypeScript/Vite verifica tipos e empacotamento. O audit npm foi checado no conjunto instalado; uma consulta limpa hoje não garante ausência de problemas futuros.

### Navegador

O roteiro local inicia API e frontend, cria pedido, inicia preparo, conclui, registra recebimento, confirma aprovação, inicia e pausa simulador, filtra período vazio e limpa. Captura as seis áreas em três larguras e dois idiomas, verifica erros JavaScript e largura do corpo. O painel Streamlit também é aberto com dados. O script é um apoio de verificação e não um serviço em segundo plano no computador do usuário.

### CI

O workflow prepara Python com uv e versão travada, roda pytest e prepara o pipeline. Outro job roda npm ci, Vitest e build. Essa configuração foi executada localmente e no GitHub. Em 11/11/2026 os jobs Python e frontend terminaram com sucesso na execução 43042107497 do repositório público natandata/restaurante-operacao-dados.

### Falhas úteis para demonstrar

Tentar pedido sem ingrediente deve deixar estoque igual. Tentar aprovar recebimento duas vezes não deve duplicar entrada. Reenviar a mesma chave com payload diferente deve dar conflito. Um CSV com chave de pedido inexistente deve rejeitar todo o lote. Alterar o último alvo da série não deve mudar features dos dias anteriores. Cada uma dessas falhas ensina uma decisão de projeto, não apenas sintaxe.

### Arquivos para estudar

- `tests/test_platform.py`
- `tests/test_domain.py`
- `frontend/src/lib.test.ts`
- `.github/workflows/ci.yml`

## Ambiente e execução

Executar localmente, sem cartão, sem serviço de IA e sem publicar automaticamente.

### Pré-requisitos

Para a pilha completa, usar Python 3.12 e uv, Node22 com npm e Git. As dependências estão em pyproject.toml/uv.lock e package.json/package-lock.json. O módulo01 roda com a biblioteca padrão; a plataforma completa precisa instalar dependências. O módulo01 foi testado com Python3.14; a plataforma completa foi verificada com Python3.12 em ambiente separado. Isso não confirma compatibilidade de toda a pilha com Python3.14 nem instalação na máquina de destino.

### Preparação

Na raiz: uv sync --locked --python 3.12. Depois: uv run python scripts/prepare.py. O script preserva o conjunto existente se houver manifest, valida/importa, executa dbt build e calcula previsão. No frontend: npm ci --ignore-scripts e npm run build. Não usar npm audit fix --force sem avaliar mudanças. O pacote não pede token de API, senha de GitHub ou dados de cartão.

### Iniciar aplicações

Terminal 1, na raiz: uv run uvicorn operacao.api:app --host 127.0.0.1 --port 8000. Terminal 2, em frontend/: npm run dev -- --port 5173. Abrir http://127.0.0.1:5173 no próprio computador. Terminal 3, opcional, na raiz: uv run streamlit run app/Home.py. O painel usa a porta8501. Para encerrar, Ctrl+C em cada terminal que você abriu, sem finalizar outros programas.

### Testar

Na raiz: uv run python -m pytest -q. Em frontend/: npm run test e npm run build. Os testes de pipeline criam dados temporários pequenos e banco separado. Não executar scripts de limpeza no diretório de dados do usuário para “fazer teste passar”. O backend pode criar seu banco operacional local ao iniciar; isso é esperado e não é dado de cliente.

### Instalação com cuidado

Antes de instalar a pilha completa no computador de trabalho, confira espaço livre e memória, mantenha a primeira versão intacta e não encerre outros aplicativos. Instalar por terminal permite preservar o uso normal do computador. O teste do primeiro módulo não confirma sozinho a instalação de todo o projeto.

### Arquivos para estudar

- `pyproject.toml`
- `scripts/prepare.py`
- `frontend/package.json`

## Como modificar sem perder o controle

Uma contribuição autoral aparece no raciocínio, nos testes e nas escolhas, não em retirar uma linha de crédito.

### Adicionar produto

Defina identificador novo, nome fictício, categoria, preço/custo em centavos e receita em unidades-base. Escreva teste de reserva e consumo e confira ingrediente compartilhado. O catálogo do Store é inicializado com INSERT OR IGNORE: editar settings não atualiza automaticamente um produto já existente no banco. Uma evolução segura exige migração explícita ou cenário novo; não apagar o banco silenciosamente.

### Novo indicador

Escreva a pergunta e o grão, depois a fórmula, fontes e exclusões. Crie SQL no warehouse usando ref. Acrescente teste de reconciliação e um caso que possa calcular à mão. Só depois adicione o nome ao mapa permitido da API e a apresentação. Não criar endpoint que aceite SQL livre do navegador. Informe se o indicador é do período filtrado ou global.

### Nova regra de cancelamento

Cancelar depois do preparo não deve simplesmente repor todos os ingredientes. Primeiro decida quais podem voltar e quais são perda; registre compensação com motivo. Adicione testes de transição e duas tentativas concorrentes. Preserve a trilha anterior. Se a regra mudar para “cancelar tudo”, a demonstração ficaria fácil mas o negócio ficaria errado.

### Novo modelo de previsão

Implemente um candidato atrás da mesma função de previsão, sem mudar o teste final depois de olhar seu resultado. Compare em validação. Refaça teste somente com a seleção congelada. Documente custo, tempo e premissas. Não promover um modelo apenas porque parece mais avançado. O baseline de semana anterior é parte do produto de estudo, não uma etapa descartável.

### Histórico ao vivo no warehouse

Para unir os contextos, proponha uma tabela raw de eventos com seq como chave e um cursor de extração transacional. Leia eventos novos sem duplicar, reconcilie estado e preserve evento cancelado. Não misture simplesmente um CSV anual com pedidos ao vivo sem distinguir origem e data. Esse é um bom próximo incremento independente, mas não deve ser apresentado como já feito.

### Arquivos para estudar

- `operacao/settings.py`

## Falhas comuns e como investigar

Investigar o sintoma antes de substituir ferramentas ou apagar dados.

### Sem API ou reconectando

Confira se o terminal do uvicorn está aberto, escutando127.0.0.1:8000 e sem erro. Abra /api/health localmente. Se o frontend está em outra porta, a origem pode não estar permitida: use a porta documentada antes de mudar CORS. Não expor a API na rede para contornar erro de porta.

### Warehouse ausente

A operação ao vivo pode funcionar sem histórico preparado. As análises e previsão precisam de scripts/prepare.py. Leia o erro no terminal. Uma raw carregada sem dbt não é um warehouse concluído. Verifique que você rodou da raiz, usando profiles-dir warehouse. Não invente um gráfico com zeros para esconder a falta de tabela.

### Destino do gerador não vazio

O gerador recusa sobrescrita de propósito. Escolha outra pasta com --out para experimentar. Não apague uma pasta com resultados de estudo só porque a execução disse existir. Se precisar manter vários cenários, use bancos e caminhos separados e registre a configuração usada.

### Lote rejeitado

Abra rejections.json junto ao lote. Corrija a causa na fonte ou gere outro cenário, mantendo o erro como caso de teste. Não remover validação para deixar passar uma chave inexistente. O banco deve permanecer igual depois da rejeição; há teste para isso.

### Estoque insuficiente no simulador

O simulador consome estoque e não recebe automaticamente. Pause. Registre um recebimento fictício da quantidade/unidade desejada e aprove uma vez. Depois retome. Isso demonstra o fluxo de decisão e é diferente de um serviço externo reabastecendo de verdade.

### Número de teste ou resultado mudou

Confira versão do código, lockfiles, semente e parâmetro de geração. O número de testes pode aumentar e as métricas podem mudar quando o cenário muda. Não editar a documentação para prometer o resultado anterior sem reproduzi-lo. Guarde comandos e saídas úteis sem incluir segredos ou conteúdo de contas.

## Decisões, limites e demonstração

Ser claro sobre o que não existe torna a apresentação mais confiável.

### Decisões defendíveis

Dinheiro em centavos; unidade-base por ingrediente; reserva separada de consumo; transações para proteger um pedido inteiro; comandos com chaves; eventos sequenciais; raw validada e marts em SQL; seleção de modelo fora do teste; contextos histórico e ao vivo separados; visual da marca aplicado a tarefas operacionais. Cada decisão pode ser apontada no código e ligada a um teste.

### Limites técnicos

Não há autenticação, backup/restore automatizado, migração de schema, concorrência distribuída, múltiplos workers de simulação, integração real, intervalos de previsão calibrados ou escala otimizada. O Store inicializa catálogo uma vez e não migra alterações automaticamente. O histórico é snapshot e a API retorna até500 pedidos recentes. Não há alegação de testes exaustivos ou aprovação de produção.

### Limites de negócio

Toda demanda, custo, preço, comissão, presença, avaliação e clima é sintético ou ilustrativo. Não há clientes, ganhos ou resultados reais. “Contribuição” não é lucro líquido. A sugestão de pessoas é uma conta demonstrativa com premissas, não recomendação de RH. A interface não movimenta dinheiro nem faz pedido a fornecedor.

### Roteiro de cinco minutos

1. Explique o aviso sintético. 2. Crie um pedido e mostre a reserva. 3. Inicie preparo e mostre físico versus disponível. 4. Registre recebimento e demonstre que pendente não altera saldo; aprove. 5. Abra análise e siga um indicador ao SQL. 6. Mostre baseline, seleção em validação e teste. 7. Termine com uma limitação e uma evolução específica. Não dizer que usou em produção se não usou.

### Publicação ainda depende de revisão

Antes do GitHub, revisar nome, README, arquivos, licença do código próprio e audiência. Não incluir bancos, CSVs grandes, ambientes, node_modules, material privado, manual completo, credenciais ou logs de contas. Screenshots devem mostrar só a aplicação sintética. A presença de uma configuração de CI não prova que ela rodou no GitHub. Não criar convite ou link público antes da revisão.

## Glossário e mapa de leitura

Termos técnicos em palavras simples.

### Grão

O que uma linha representa. Uma linha por pedido é diferente de uma linha por produto de um pedido. Agregar sem respeitar isso duplica receita.

### Idempotência

Repetir a mesma solicitação identificada não cria um segundo efeito. Requer chave e comparação de conteúdo, não só confiar que o botão foi clicado uma vez.

### Transação

Um grupo de mudanças que é confirmado inteiro ou desfeito inteiro. Aqui protege pedido, movimentos, eventos e resposta de comando.

### Mart

Tabela já organizada para uma pergunta de análise. Não é um segundo banco mágico; é SQL calculado em cima de fatos e dimensões.

### Lag e janela móvel

Lag consulta valor anterior na série. Média móvel calcula uma janela. Para previsão, a janela deve parar antes do dia a prever.

### Validação e teste

Validação ajuda a escolher o modelo. Teste mede a escolha congelada. Olhar o teste para ajustar repetidamente destrói essa separação.

### WebSocket

Conexão que permite ao serviço enviar atualizações sem o navegador fazer uma nova consulta para cada evento. A API HTTP continua sendo útil para recuperar estado.

### Baseline

Referência simples que um método mais complexo precisa justificar superar no mesmo recorte de avaliação. Aqui repetir semana anterior e média de sete dias.

### Como revisar um arquivo

Comece pela responsabilidade e entradas, acompanhe a mudança de estado ou retorno, identifique o que pode falhar, abra o teste correspondente e faça um exemplo pequeno. Não memorize cada linha: explique a decisão que ela implementa.
