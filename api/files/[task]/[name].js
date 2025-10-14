const fs = require('fs');
const path = require('path');

module.exports = (req, res) => {
  const { task, name } = req.query;
  console.log('files handler:', { method: req.method, task, name });
  const filePath = path.join('/tmp', task || '', name || '');
  if (!fs.existsSync(filePath)) return res.status(404).send('Not found');
  return res.sendFile(filePath);
};
