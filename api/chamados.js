import { neon } from '@neondatabase/serverless';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PATCH, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();

  try {
    const sql = neon(process.env.DATABASE_URL);

    await sql`
      CREATE TABLE IF NOT EXISTS chamados (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        setor TEXT NOT NULL,
        assunto TEXT NOT NULL,
        descricao TEXT,
        prioridade TEXT DEFAULT 'Baixa',
        status TEXT DEFAULT 'Aberto',
        tecnico TEXT DEFAULT '',
        data TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
      )
    `;

    if (req.method === 'GET') {
      const rows = await sql`SELECT * FROM chamados ORDER BY id DESC`;
      return res.status(200).json(rows);
    }

    if (req.method === 'POST') {
      const { nome, setor, assunto, descricao, prioridade, data } = req.body;
      if (!nome || !setor || !assunto) {
        return res.status(400).json({ error: 'Campos obrigatórios faltando' });
      }
      const rows = await sql`
        INSERT INTO chamados (nome, setor, assunto, descricao, prioridade, status, tecnico, data)
        VALUES (${nome}, ${setor}, ${assunto}, ${descricao || ''}, ${prioridade || 'Baixa'}, 'Aberto', '', ${data || ''})
        RETURNING *
      `;
      return res.status(201).json(rows[0]);
    }

    if (req.method === 'PATCH') {
      const id = req.query.id;
      const { tecnico, status } = req.body;
      if (!id) return res.status(400).json({ error: 'ID obrigatório' });
      const rows = await sql`
        UPDATE chamados
        SET tecnico = ${tecnico ?? ''}, status = ${status ?? 'Aberto'}
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
}
