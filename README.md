# PutioMount
Mount put.io as a drive using python

## Retrieving a token
1) Go to https://put.io/oauth/apps/new , create an app (fill something in all fields, it does not matter)  
2) Go to https://put.io/oauth/apps , and click on the "key" icon, next to your app name  
3) Last field contains your token. Paste it in the /home/YOUR-USERNAME/.putio-token, instead of "YOUR_TOKEN_HERE"

## Installation
```bash
$ python setup.py install
```

## Usage
```bash
$ python ./putiomount.py /destination/folder
```

## Advanced usage
If you want to use PutioMount as a library, you can install it using pip:
```bash
$ pip install PutioMount
```

And use it:
```python
import PutioMount

# Set a custom temporary path
PutioMount.set_tmp_path('/tmp')

# Set a custom credentials path
PutioMount.set_credentials_path('/path/to/.credentials')

# List mp4 files if available instead of original files
# 
# Need to install specific package
# pip install git+https://github.com/gpenverne/putio.py
PutioMount.set_prefer_mp4()

# Mount to specific path
PutioMount.mount('/my/mount/point')
```

## Issues
Upgrade requests and urllib3:
```bash
$ pip install -U urllib3
$ pip install -U requests
```

Check if fuse is installed:
```bash
$ apt-get install fuse
```
