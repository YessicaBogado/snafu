# Snafu: Snake Functions - Web Connector

from flask import Flask, abort, send_file
import json
import zipfile
import threading
import os
import configparser

app = Flask("snafu")
gcb = None


@app.route('/invoke/<function>/<args>')
def invoke(function, args):
    function = function
    response = gcb(function, web=True, args=args)
    if not response:
        abort(500)
    return response


@app.route('/invoke/<function>/')
def invoke_args(function):
    function = function
    response = gcb(function, web=True, re_args=True)
    if not response:
        abort(500)
    return response


@app.route("/functions/funHub")
def funcHub():
    """Return the listFun for FunctionHub."""
    try:
        mypath = os.getcwd()
        json_data = open(mypath + "/listFun").read()
        data = json.loads(json_data)
        print(data)
        return json.dumps(data)
    except Exception as e:
        print(str(e))


@app.route("/function-download/<function>.zip")
def functiondownload(function):
    mypath = os.getcwd()
    json_data = open(mypath + "/listFun").read()
    data = json.loads(json_data)
    for i in data:
        if i["title"] == function:
            function_info = i
            break
    try:
        path = str(function_info["source"])
        print(path)
        if ".class" in path:
            path = path.replace('.class', '.java')
        if ".so" in path:
            path = path.replace('.so', '.c')
        pathZip = str(os.getcwd()) + "/" + function_info["title"] + ".zip"
        funZip = zipfile.ZipFile(pathZip, 'w')
        funZip.write(path, os.path.basename(path),
                     compress_type=zipfile.ZIP_DEFLATED)
        funZip.close()
    except Exception as e:
        err = json.dumps({"errorMessage": "NoZipFilePresent " +
                          str(function)})
        print(str(e))
        return err, 501
    return send_file(pathZip, mimetype="application/zip",
                     as_attachment=True)


def initinternal(function, configpath):
    connectconfig = None
    if not configpath:
        configpath = "snafu.ini"
    if not function:
        function = "snafu"
    if os.path.isfile(configpath):
        config = configparser.ConfigParser()
        config.read(configpath)
        if function in config and "connector.web" in config[function]:
            connectconfig = int(config[function]["connector.web"])
    if connectconfig:
        app.run(host="0.0.0.0", port=connectconfig)


def init(cb, function=None, configpath=None):
    global gcb
    gcb = cb
    t = threading.Thread(target=initinternal, daemon=True,
                         args=(function, configpath))
    t.start()
