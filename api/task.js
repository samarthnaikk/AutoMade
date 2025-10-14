const fs = require('fs');
const path = require('path');

function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function parseDataUri(uri) {
  const m = uri.match(/^data:([^;]+);base64,(.+)$/);
  if (!m) return null;
  return { mime: m[1], data: Buffer.from(m[2], 'base64') };
}

function dumpRequest(req) {
  return {
    method: req.method,
    headers: req.headers,
    url: req.url,
    query: req.query,
    body: req.body,
  };
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Method not allowed' });
  }

  console.log('Incoming request:', JSON.stringify(dumpRequest(req)));

  let payload = req.body || null;
  if (!payload && req.rawBody) {
    try {
      payload = JSON.parse(req.rawBody.toString('utf8'));
    } catch (e) {
      payload = null;
    }
  }

  const task = (payload && payload.task) || `task-${Date.now()}`;
  const baseDir = path.join('/tmp', task);
  ensureDir(baseDir);

  fs.writeFileSync(path.join(baseDir, 'payload.json'), JSON.stringify(payload || {}, null, 2));

  const attachments = (payload && payload.attachments) || [];
  const meta = {};
  for (const att of attachments) {
    const name = att.name || `attachment-${Date.now()}`;
    const parsed = parseDataUri(att.url || '');
    if (!parsed) continue;
    const out = path.join(baseDir, path.basename(name));
    fs.writeFileSync(out, parsed.data);
    meta[name] = { mime: parsed.mime };
  }

  let imgUrl = null;
  const brief = (payload && payload.brief) || '';
  const m = brief.match(/\?url=([^\s]+)/);
  if (m) imgUrl = m[1];
  else if (Object.keys(meta).length > 0) imgUrl = `/files/${task}/${Object.keys(meta)[0]}`;

  let solved = null;
  if (imgUrl && imgUrl.startsWith('/files/')) {
    const name = imgUrl.split('/').pop();
    const digits = name.match(/(\d+)/);
    solved = digits ? digits[0] : 'solved';
  }

  // Build view URL
  const host = req.headers['x-forwarded-host'] || req.headers.host || 'localhost';
  const proto = req.headers['x-forwarded-proto'] || 'https';
  const viewUrl = `${proto}://${host}/view/${encodeURIComponent(task)}`;

  return res.json({ task, view_url: viewUrl, image_url: imgUrl, solved, received_request: dumpRequest(req) });
};
