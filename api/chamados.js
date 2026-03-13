import { sql } from '@vercel/postgres';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();

  try {
    // CREATE TABLE if not exists
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

    // GET - listar todos
    if (req.method === 'GET') {
      const { rows } = await sql`SELECT * FROM chamados ORDER BY id DESC`;
      return res.status(200).json(rows);
    }

    // POST - criar novo chamado
    if (req.method === 'POST') {
      const { nome, setor, assunto, descricao, prioridade, data } = req.body;
      if (!nome || !setor || !assunto) {
        return res.status(400).json({ error: 'Campos obrigatórios faltando' });
      }
      const { rows } = await sql`
        INSERT INTO chamados (nome, setor, assunto, descricao, prioridade, status, tecnico, data)
        VALUES (${nome}, ${setor}, ${assunto}, ${descricao || ''}, ${prioridade || 'Baixa'}, 'Aberto', '', ${data || ''})
        RETURNING *
      `;
      return res.status(201).json(rows[0]);
    }

    // PATCH - atualizar chamado
    if (req.method === 'PATCH') {
      const { id } = req.query;
      const { tecnico, status } = req.body;
      if (!id) return res.status(400).json({ error: 'ID obrigatório' });
      const { rows } = await sql`
        UPDATE chamados
        SET tecnico = ${tecnico ?? ''}, status = ${status ?? 'Aberto'}
        WHERE id = ${id}
        RETURNING *
      `;
      return res.status(200).json(rows[0]);
    }

    return res.status(405).json({ error: 'Método não permitido' });

  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: 'Erro interno', detail: err.message });
  }
}
