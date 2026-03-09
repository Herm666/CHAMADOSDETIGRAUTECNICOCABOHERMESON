# TI Suporte — Sistema de Chamados

Portal de abertura e gerenciamento de chamados de TI com backend Python e banco de dados SQLite.

---

## Estrutura do Projeto

```
ti-suporte/
├── backend/
│   └── server.py          ← API REST (Python 3, sem dependências externas)
├── data/
│   └── chamados.db        ← Banco SQLite (criado automaticamente)
├── frontend/
│   ├── solicitante.html   ← Portal do usuário (abrir chamado)
│   └── tecnico.html       ← Painel do técnico (gerenciar chamados)
├── iniciar.sh             ← Script de inicialização (Linux/Mac)
└── README.md
```

---

## Como Usar

### 1. Iniciar o backend

```bash
# Linux / Mac
bash iniciar.sh

# Ou manualmente:
python3 backend/server.py
```

O servidor inicia na **porta 5000**.

### 2. Abrir o frontend

Abra os arquivos HTML diretamente no navegador:

- **Portal do Solicitante:** `frontend/solicitante.html`
- **Painel do Técnico:** `frontend/tecnico.html`

> ⚠️ O backend precisa estar rodando para o frontend funcionar.

---

## API REST

| Método | Rota                    | Descrição                          |
|--------|-------------------------|------------------------------------|
| GET    | `/api/chamados`         | Listar todos os chamados           |
| GET    | `/api/chamados/stats`   | Estatísticas do dashboard          |
| GET    | `/api/chamados/:id`     | Detalhe de um chamado              |
| POST   | `/api/chamados`         | Criar novo chamado                 |
| PUT    | `/api/chamados/:id`     | Atualizar chamado (status/técnico) |
| DELETE | `/api/chamados/:id`     | Remover chamado                    |

### Filtros disponíveis (GET /api/chamados)

```
?status=Aberto
?prioridade=Alta
?tecnico=HermesonTI
?setor=Comercial
?q=impressora       ← busca por nome, assunto ou descrição
?limit=10
```

### Exemplo: Criar chamado

```bash
curl -X POST http://localhost:5000/api/chamados \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "João Silva",
    "setor": "Comercial",
    "assunto": "Impressora não imprime",
    "descricao": "Erro ao tentar imprimir documentos PDF",
    "prioridade": "Média"
  }'
```

### Exemplo: Atualizar status

```bash
curl -X PUT http://localhost:5000/api/chamados/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "Concluído", "tecnico": "HermesonTI"}'
```

---

## Banco de Dados

O banco SQLite é criado automaticamente em `data/chamados.db` na primeira execução.

### Estrutura da tabela `chamados`

| Campo       | Tipo    | Descrição                              |
|-------------|---------|----------------------------------------|
| id          | INTEGER | Chave primária (auto-incremento)       |
| nome        | TEXT    | Nome do solicitante                    |
| setor       | TEXT    | Setor do solicitante                   |
| assunto     | TEXT    | Título do chamado                      |
| descricao   | TEXT    | Descrição detalhada                    |
| prioridade  | TEXT    | Baixa / Média / Alta                   |
| status      | TEXT    | Aberto / Em Atendimento / Concluído    |
| tecnico     | TEXT    | Técnico responsável                    |
| data        | TEXT    | Data formatada (pt-BR)                 |
| data_iso    | TEXT    | Data em formato ISO 8601               |
| updated_at  | TEXT    | Última atualização (ISO 8601)          |

---

## Requisitos

- Python 3.8+ (módulos `sqlite3`, `http.server`, `json` — todos nativos)
- Navegador moderno (Chrome, Firefox, Edge)

Nenhuma instalação de pacotes extras é necessária.

---

## Equipe

HermesonTI · Emanoel Estagiário · Ghabriel Estagiário
