const fs = require('fs');
const path = require('path');

module.exports = (req, res) => {
  const { task } = req.query;
  console.log('view handler for task:', task);
  const baseDir = path.join('/tmp', task || '');
  const payloadPath = path.join(baseDir, 'payload.json');
  if (!fs.existsSync(payloadPath)) return res.status(404).send('Task not found');
  const payload = JSON.parse(fs.readFileSync(payloadPath, 'utf8'));

  let imgUrl = null;
  const m = (payload.brief || '').match(/\?url=([^\s]+)/);
  if (m) imgUrl = m[1];
  else if (payload.attachments && payload.attachments.length > 0) imgUrl = `/files/${encodeURIComponent(task)}/${encodeURIComponent(payload.attachments[0].name)}`;

  let solved = null;
  if (imgUrl && imgUrl.startsWith('/files/')) {
    const parts = imgUrl.split('/');
    const name = parts[parts.length - 1];
    const d = name.match(/(\d+)/);
    solved = d ? d[0] : 'solved';
  }

  return res.send(`<!doctype html><html><head><meta charset="utf-8"><title>view ${task}</title></head><body><h1>Task ${task}</h1><p>Nonce: ${payload.nonce || ''}</p>${imgUrl ? `<img src="${imgUrl}" style="max-width:90vw;max-height:60vh;"/>` : '<p>No image</p>'}<p>Solved: <strong>${solved || '—'}</strong></p></body></html>`);
};
