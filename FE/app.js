var express = require('express');
var path = require('path');
var app = express();

app.use(express.json());
const cookieParser = require('cookie-parser');
app.use(cookieParser());

app.get('/', (req, res)=> {
    res.sendFile(path.join(__dirname+'/index.html'));
})
var PORT = 1234
app.listen(PORT, () => {
  console.log(`Listening at port ${PORT}`);
})