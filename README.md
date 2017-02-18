# putio-mount
Mount put.io as a drive on linux

## Retrieving a token
1) Go to https://put.io/oauth/apps/new , create an app (fill something in all fields, it does not matter)  
2) Go to https://put.io/oauth/apps , and click on the "key" icon, next to your app name  
3) Last field contains your token. Paste it in the .credentials.json:
```
{
  "token": "YOUR TOKEN HERE"
}
```

## Usage
```bash
$ python ./putiomount.py /destination/folder
```
