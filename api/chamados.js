import { neon } from '@neondatabase/serverless';

const sql = neon(process.env.DATABASE_URL);

async function initDB() {
  // Adiciona colunas que podem não existir na tabela original
  await sql`ALTER TABLE chamados ADD COLUMN IF NOT EXISTS historico JSONB DEFAULT '[]'`;
  await sql`ALTER TABLE chamados ADD COLUMN IF NOT EXISTS notas JSONB DEFAULT '[]'`;
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();

  await initDB();

  try {
    // GET — listar todos
    if (req.method === 'GET') {
      const rows = await sql`SELECT * FROM chamados ORDER BY id DESC`;
      // Normaliza 'nome' para 'solicitante' para o frontend
      const normalized = rows.map(r => ({ ...r, solicitante: r.nome }));
      return res.status(200).json(normalized);
    }

    // POST — criar novo chamado
    if (req.method === 'POST') {
      const { assunto, solicitante, setor, prioridade, descricao } = req.body;
      if (!assunto || !solicitante || !setor) {
        return res.status(400).json({ error: 'Campos obrigatórios ausentes' });
      }
      const historico = JSON.stringify([{ msg: 'Chamado aberto via portal', time: Date.now() }]);
      const rows = await sql`
        INSERT INTO chamados (nome, setor, assunto, descricao, prioridade, status, historico)
        VALUES (${solicitante}, ${setor}, ${assunto}, ${descricao || ''}, ${prioridade || 'Média'}, 'Aberto', ${historico})
        RETURNING *
      `;
      const r = rows[0];
      return res.status(201).json({ ...r, solicitante: r.nome });
    }

    // PUT — atualizar chamado
    if (req.method === 'PUT') {
      const { id, status, tecnico, historico, notas } = req.body;
      if (!id) return res.status(400).json({ error: 'ID obrigatório' });
      const rows = await sql`
        UPDATE chamados SET
          status    = COALESCE(${status ?? null}, status),
          tecnico   = COALESCE(${tecnico ?? null}, tecnico),
          historico = COALESCE(${historico ? JSON.stringify(historico) : null}::jsonb, historico),
          notas     = COALESCE(${notas ? JSON.stringify(notas) : null}::jsonb, notas)
        WHERE id = ${id}
        RETURNING *
      `;
      if (!rows.length) return res.status(404).json({ error: 'Chamado não encontrado' });
      const r = rows[0];
      return res.status(200).json({ ...r, solicitante: r.nome });
    }

    return res.status(405).json({ error: 'Método não permitido' });

  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: 'Erro interno', detail: err.message });
  }
}
