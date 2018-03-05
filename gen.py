#! /usr/bin/env python3

"""Create the listFun."""

import json
import os
import random
import sys

BASEPATH = os.environ['HOME']

if len(sys.argv) == 2:
    BASEPATH = sys.argv[1]

try:
    import snafulib.snafu as snafu
except ImportError:
    import snafu

# required for executors
origdir = BASEPATH
os.chdir(BASEPATH)

snafu = snafu.Snafu(False)
snafu.activate([os.path.join(BASEPATH, "functions"),
                os.path.join(BASEPATH, "functions-local")], "any", ignore=True)

allfunctions = []

for idnum, funcname in enumerate(snafu.functions):
    func, unclear, source = snafu.functions[funcname]
    print(funcname, func, unclear, source.source)
    save_funcname = funcname
    language = source.source.split(".")[-1]

    if "." in funcname:
        funcname = funcname.split(".")[0]

    languagenames = {}
    languagenames["c"] = "C"
    languagenames["so"] = "compiled C"
    languagenames["py"] = "Python"
    languagenames["pyc"] = "bytecode-compiled Python"
    languagenames["java"] = "Java"
    languagenames["class"] = "bytecode-compiled Java"
    languagenames["js"] = "JavaScript (Node.js)"

    languagename = "unknown"
    if language in languagenames:
        languagename = languagenames[language]

    newfunction = {}
    newfunction["id"] = idnum
    newfunction["title"] = funcname
    newfunction["source"] = source.source
    newfunction["funcname"] = save_funcname
    newfunction["sla"] = (
        "Subject to terms and conditions."
        "No warranty for free service offerings.")
    newfunction["description"] = "A {} function.".format(languagename)
    newfunction["icon"] = "img/icon/{}.png".format(language)
    newfunction["access"] = "public"
    newfunction["provider_name"] = "Service Prototyping Lab"
    newfunction["provider_www"] = "http://serviceprototypinglab.github.io/"
    newfunction["location"] = "Winterthur, CH"
    newfunction["end_points"] = [{"type": "muc", "priority": "main",
                                  "name": "xmpp://", "pwd": None}]

    if os.path.isfile(".".join(source.source.split(".")[:-1]) + ".config"):
        newfunction["description"] += (
            " This function has been imported from AWS Lambda.")

    if "functions-local" not in source.source:
        # newfunction["access"] = "private"
        newfunction["end_points"].append(2)
        if random.random() < 0.3:
            newfunction["end_points"].append(3)

    if random.random() < 0.4:
        newfunction["preview"] = ["img/preview/1.png", "img/preview/2.png"]

    allfunctions.append(newfunction)

os.chdir(origdir)
f = open("listFun", "w")
json.dump(allfunctions, f)
f.close()
