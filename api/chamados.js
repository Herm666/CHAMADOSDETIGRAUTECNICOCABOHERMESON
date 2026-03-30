const { neon } = require('@neondatabase/serverless');

const sql = neon(process.env.DATABASE_URL);

async function initDB() {
  await sql`
    CREATE TABLE IF NOT EXISTS chamados (
      id          SERIAL PRIMARY KEY,
      assunto     TEXT NOT NULL,
      solicitante TEXT NOT NULL,
      setor       TEXT NOT NULL,
      prioridade  TEXT NOT NULL DEFAULT 'Média',
      descricao   TEXT DEFAULT '',
      status      TEXT NOT NULL DEFAULT 'Aberto',
      tecnico     TEXT DEFAULT '',
      historico   JSONB DEFAULT '[]',
      notas       JSONB DEFAULT '[]',
      data        TIMESTAMPTZ DEFAULT NOW()
    )
  `;
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();

  await initDB();

  try {
    if (req.method === 'GET') {
      const rows = await sql`SELECT * FROM chamados ORDER BY id DESC`;
      return res.status(200).json(rows);
    }

    if (req.method === 'POST') {
      const { assunto, solicitante, setor, prioridade, descricao } = req.body;
      if (!assunto || !solicitante || !setor) {
        return res.status(400).json({ error: 'Campos obrigatórios ausentes' });
      }
      const historico = JSON.stringify([{ msg: 'Chamado aberto via portal', time: Date.now() }]);
      const rows = await sql`
        INSERT INTO chamados (assunto, solicitante, setor, prioridade, descricao, historico)
        VALUES (${assunto}, ${solicitante}, ${setor}, ${prioridade || 'Média'}, ${descricao || ''}, ${historico})
        RETURNING *
      `;
      return res.status(201).json(rows[0]);
    }

    if (req.method === 'PUT') {
      const { id, status, tecnico, historico, notas } = req.body;
      if (!id) return res.status(400).json({ error: 'ID obrigatório' });
      const rows = await sql`
        UPDATE chamados SET
          status    = COALESCE(${status}, status),
          tecnico   = COALESCE(${tecnico}, tecnico),
          historico = COALESCE(${historico ? JSON.stringify(historico) : null}::jsonb, historico),
          notas     = COALESCE(${notas ? JSON.stringify(notas) : null}::jsonb, notas)
        WHERE id = ${id}
        RETURNING *
      `;
      if (!rows.length) return res.status(404).json({ error: 'Chamado não encontrado' });
      return res.status(200).json(rows[0]);
    }

    return res.status(405).json({ error: 'Método não permitido' });

  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: 'Erro interno', detail: err.message });
  }
};
