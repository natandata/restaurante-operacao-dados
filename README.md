# Restaurante: operação e dados

Implementação independente de uma plataforma local de estudo para um restaurante fictício, com identidade visual data with natan. Repositório público autorizado após revisão de nome, README, arquivos e audiência.

Código, telas e dados foram escritos para este projeto com assistência de IA. Não representam trabalho feito sozinho, uso em cliente ou resultado comercial. Não foi reutilizado código, texto, dados ou assets do repositório que motivou o estudo. As licenças de bibliotecas e da fonte Inter continuam aplicáveis.

## O que existe

- Operação persistente em SQLite: pedidos, reserva, preparo, conclusão, cancelamento antes do preparo, movimentos de estoque e recebimentos com aprovação separada.
- Comandos com chave de idempotência, transações, teste de concorrência e eventos com sequência persistente.
- Gerador próprio reproduzível: 11 CSVs de entidades e eventos fictícios, com receitas, canais, equipe, fornecedores, clima e avaliações simulados.
- Ingestão de lote inteiro com validação, rejeições, hash e substituição atômica do snapshot raw em DuckDB.
- Warehouse dbt: 11 views de staging, um intermediário, seis dimensões, seis fatos e sete marts. 31 modelos e 32 testes de dados.
- Análises de vendas, contribuição, cardápio, canais, atendimento, equipe, estoque e avaliações.
- Previsão com quatro candidatos, seleção em validação temporal, teste separado e sete dias recursivos. Sem intervalo calibrado ou prova de desempenho real.
- FastAPI, OpenAPI e WebSocket com snapshot, eventos, cursor e reconexão no cliente.
- React/TypeScript com seis áreas em PT/EN e interface responsiva; painel histórico Streamlit com oito análises.
- Testes Python e frontend, configuração de CI e guia aprofundado com decisões, código, execução e caminhos de modificação.

## Rodar

Pré-requisitos para a plataforma: Python 3.12, uv e Node 22/npm. Sem conta, token de IA, Docker, cartão ou serviço pago.

Na raiz do projeto:

```bash
uv sync --locked --python 3.12
uv run python scripts/prepare.py
uv run python -m pytest -q
```

A preparação gera o cenário se ainda não houver manifest, valida/importa o lote, constrói o warehouse e calcula a previsão. Não substitui silenciosamente um diretório de geração existente. A geração anual padrão tem 365 dias; o cenário é histórico e suas datas não acompanham o dia de hoje.

Terminal 1, na raiz:

```bash
uv run uvicorn operacao.api:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
cd frontend
npm ci --ignore-scripts
npm run dev -- --port 5173
```

Abra `http://127.0.0.1:5173` no mesmo computador. A documentação local da API fica em `http://127.0.0.1:8000/docs`.

Painel complementar, em outro terminal na raiz:

```bash
uv run streamlit run app/Home.py --server.address 127.0.0.1
```

Abra a porta 8501. Para encerrar, use Ctrl+C nos terminais dessas aplicações. Não finalize outros programas.

## Testar

```bash
# raiz
uv run python -m pytest -q

# frontend
cd frontend
npm test
npm run build
```

Verificação local desta versão: 37 testes Python e quatro subcasos, 7 testes frontend, build TypeScript/Vite e 63 etapas dbt (31 modelos + 32 testes). O fluxo de navegador exercitou pedido, preparo, conclusão, recebimento, aprovação, simulador, filtro vazio e limpeza. As seis áreas React foram capturadas em PT/EN nas larguras 320, 390 e 1280px; as oito análises Streamlit também foram abertas. Há um aviso de depreciação da integração de testes Starlette/httpx, sem falha de execução.

O workflow `.github/workflows/ci.yml` está configurado, mas ainda não houve execução remota no GitHub desta entrega. Não há badge de sucesso remoto.

## Arquitetura

```text
CSV sintético → validação de lote → DuckDB raw → dbt → marts → análise e previsão

Comando HTTP → transação SQLite → pedido/movimentos/evento → WebSocket → React
```

Histórico e operação ao vivo são contextos separados. Os pedidos da interface não são incorporados automaticamente ao histórico anual. As telas deixam essa diferença explícita.

| Pasta | Responsabilidade |
| --- | --- |
| `operacao/` | domínio, persistência, geração, ingestão, previsão e API |
| `warehouse/` | grafo SQL/dbt e testes de dados |
| `frontend/` | interface React/TypeScript e testes de apresentação |
| `app/` | painel histórico Streamlit |
| `scripts/` | preparação do cenário completo |
| `tests/` | regras, serviço e pipeline |
| `docs/GUIA_COMPLETO.md` | manual aprofundado por módulos |
| `docs/screenshots/` | evidência visual da aplicação com dados fictícios |

## Regras principais

- Dinheiro operacional usa centavos inteiros; ingredientes usam unidade-base explícita (g ou ml).
- Reservar não reduz o saldo físico. Preparar consome físico e libera a reserva. Cancelar antes do preparo libera reserva. Concluir não consome duas vezes.
- Recebimento pendente não aumenta estoque. Aprovação aumenta uma vez, dentro de transação.
- Mesma chave e mesmo conteúdo retornam a resposta anterior; mesma chave e conteúdo diferente geram conflito.
- Lote inválido é rejeitado inteiro com `rejections.json`. Raw é o snapshot atual, não uma soma de lotes. Repetir o snapshot atual é idempotente; reimportar um lote anterior diferente restaura esse conteúdo e exige reconstruir os marts.
- A escolha de modelo usa validação, não teste. A avaliação é de um dia à frente com histórico anterior observado; o futuro de sete dias é recursivo.

## Limites

Esta é uma demonstração local, sem autenticação ou permissões por pessoa. Não exponha a API à internet. Não há pagamento, nota fiscal, integração com fornecedor, dados de cliente, backup automático, migração de schema, escala distribuída, intervalo de previsão calibrado ou escala de equipe real.

Todos os custos, taxas, demandas, clima e avaliações são fictícios. Contribuição não é lucro líquido. A sugestão de pessoas é uma conta ilustrativa, não uma decisão de RH. A interface mostra até 500 pedidos recentes; totais consultam todo o banco. Catálogo inicial é inserido uma vez: editar a configuração não migra automaticamente um banco existente.

A interface React tem PT/EN, mas detalhes de erros vindos do backend ainda podem aparecer em português. O módulo introdutório `domain.py` usa memória e consome na venda; a API usa `store.py`, com persistência e reserva antes de consumo. São etapas de estudo diferentes.

## Estudar e modificar

Comece por `docs/GUIA_COMPLETO.md`, não pela antiga primeira sessão. O guia explica os módulos, fórmulas, grãos, contratos, testes, resultados reais desta execução, limites e mudanças seguras. A especificação inicial e a primeira sessão foram arquivadas fora desta distribuição como registros superados. Não fazem parte do pacote atual nem descrevem esta versão.

Não publicar ambientes, bancos, dados gerados, `node_modules`, manual de marca privado ou credenciais. O `.gitignore` cobre os artefatos locais comuns. A fonte Inter é distribuída com seu arquivo OFL em `frontend/public/fonts/OFL.txt`. Não foi concedida uma licença de reutilização para o código próprio. A publicação pública não elimina direitos autorais nem as licenças das dependências.

### Verificação visual opcional

Depois de preparar os dados e instalar as dependências Python/frontend, rode `cd frontend`, `npx playwright install chromium` e `node verify.mjs`. O script usa o Python do ambiente `.venv` da raiz e o Chromium do Playwright. Para usar outras instalações, defina `PYTHON_BIN` e/ou `CHROME_BIN` com os executáveis completos. Mantenha as portas 8000, 5173 e 8501 livres. A execução padrão testa ações e cria pedidos/recebimentos sintéticos no banco local; use `SCREEN_ONLY=1` em um shell compatível para apenas capturar telas. Não execute contra dados reais.
