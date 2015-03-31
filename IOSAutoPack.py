#!/usr/bin/env python
#coding=utf-8

import os
import shutil
import zipfile
import glob
import subprocess
import sys
import time
import datetime

class IOSAutoPack:    
    def __init__(self, appServerURL, appleAppID, appDisplayName, appVersion, finalIPAName, customerId, modelId, p12Pass):
        Log("Create a IOSAutoPack object")
        # api访问地址
        self.appServerURL = appServerURL
        Log("AppServerUL:" + self.appServerURL)
        # app显示名称
        self.displayName = appDisplayName.decode("gbk").encode("utf-8")
        # app版本号
        self.versionNumber = appVersion
        # app在苹果商店的appID
        self.appleAppID = appleAppID
        # 证书密码
        if p12Pass == "noPass":
            self.p12Pass = "123123"
        else:
            self.p12Pass = p12Pass
        # IPA文件最终显示名称
        self.finalIPAName = finalIPAName

    def initEnvironment(self):
        '''
        初始化build环境
        '''
#        topdir = "/Users/yangshengchao/IOSAutoPackV2"
        topdir = "/Users/yangshengchao/Documents/ab"
        # Build 临时目录
        self.buildDir = os.path.join(topdir, "Build")
        if os.path.exists(self.buildDir):
            shutil.rmtree(self.buildDir)
        os.mkdir(self.buildDir)
        Log(self.buildDir)

        # 临时目录下的app文件路径
        self.buildAppDir = os.path.join(self.buildDir,"IOS.app")
        self.buildAppProvisionFile = os.path.join(self.buildAppDir, "embedded.mobileprovision")
        Log("Build App Dir:" + self.buildAppDir)
        Log("Build App Provision File:" + self.buildAppProvisionFile)

        # Entitlements 文件
        self.buildEntitlementsFile = os.path.join(self.buildDir, "IOS.xcent")
        Log("Entitlements File:" + self.buildEntitlementsFile)

        # ipa 最后存放的目录
#        self.distDir = "/Users/yangshengchao/apache-tomcat-7.0.52/webapps/IOSApkServiceV2/ipafile"
        self.distDir = "/Users/yangshengchao/Documents/ab/ipafile"
        if not os.path.exists(self.distDir):
            os.mkdir(self.distDir)
        self.targetIpaFullName = os.path.join(self.distDir, self.finalIPAName + ".ipa")

        if os.path.isfile(self.targetIpaFullName):
            os.remove(self.targetIpaFullName)

        # 拷贝 .app to build dir
        appSrcDir = os.path.join(topdir, "BaseApp/IOS.app")
        shutil.copytree(appSrcDir, self.buildAppDir)

        # 拷贝entitlements
        entitlementsSrcFile = os.path.join(topdir, "BaseApp/IOS.xcent")
        shutil.copyfile(entitlementsSrcFile, self.buildEntitlementsFile)

        # 选择证书
        self.provisionFile = os.path.join(topdir, "Certs/Provision.mobileprovision")
        Log("self.provisionFile = " + self.provisionFile)
        self.p12File = os.path.join(topdir, "Certs/ProductCert.p12")

        # 导入证书
        self.importP12_2()

    def importP12_2(self):
        # 1.  unlock keychain
        cmd = 'security unlock-keychain -p openos /Users/yangshengchao/Library/Keychains/login.keychain'
        Log(cmd)
        retCode = subprocess.call(cmd.split(' '))
        Log("security unlock-keychain Result:" + str(retCode))

        # 导入证书
        cmd = 'security import ' + self.p12File + ' -k /Users/yangshengchao/Library/Keychains/login.keychain -P ' + self.p12Pass + ' -T /usr/bin/codesign'
        Log(cmd)
        retCode = subprocess.call(cmd.split(' '))
        Log("security import-keychain Result:" + str(retCode))

        # 展示证书
        cmd = 'security find-identity -p codesigning /Users/yangshengchao/Library/Keychains/login.keychain'
        Log(cmd)
        output = os.popen(cmd).readlines()
        Log("Find-Identity Result:" + str(output))
#        ['\n',
#         'Policy: Code Signing\n',
#         '  Matching identities\n',
#         '  1) 66FC494A4937498D1FFD80594E66E4154D3FC876 "iPhone Distribution: Sichuan Tiangou Technology Co., Ltd."\n',
#         '     1 identities found\n',
#         '\n',
#         '  Valid identities only\n',
#         '  1) 66FC494A4937498D1FFD80594E66E4154D3FC876 "iPhone Distribution: Sichuan Tiangou Technology Co., Ltd."\n',
#         '     1 valid identities found\n']
        self.certUName = output[3].split('"')[1].strip()
        self.certIdentify = output[3].split('"')[0].split(')')[1].strip()
        Log("Cert UName is:" + self.certUName)
        Log("Cert Identify is:" + self.certIdentify)

        # 获得entitlement identifier (TODO:)
        self.entitleIdentifier = "L4AXYWJ5X4"#self.certUName.split('(')[1].split(')')[0]
        Log("Entitlement Identifier:" + self.entitleIdentifier)

    def deleteOriCodeSignAndEmbedProvision(self):
        Log("deleteOriCodeSignAndEmbedProvision = 0")
        # 删除XXX.app下的签名信息_CodeSignature
        codeSigDir = os.path.join(self.buildDir, "IOS.app/_CodeSignature")
        if os.path.exists(codeSigDir):
            shutil.rmtree(codeSigDir)

        Log("deleteOriCodeSignAndEmbedProvision = 1")
        # 替换.mobileprovision文件
        Log("Source Provision File:" + self.provisionFile)
        Log("Target Provision File:" + self.buildAppProvisionFile)
        shutil.copyfile(self.provisionFile, self.buildAppProvisionFile)
        Log("deleteOriCodeSignAndEmbedProvision = 2")

    def changePlist(self):
        # 修改显示的名称以及版本号
        files = []
        files.append(os.path.abspath(os.path.join(self.buildDir + "/IOS.app/Info.plist")))        

        for item in files:
            self.changePlistInternal(item, "CFBundleName", self.displayName)
            self.changePlistInternal(item, "CFBundleVersion", self.versionNumber)
            self.changePlistInternal(item, "CFBundleIdentifier", self.appleAppID)

    def changePlistInternal(self, fileName, key, value):
        cmd = []
        cmd.append('/usr/libexec/PlistBuddy')
        cmd.append('-c')
        arg = 'Set:' + key + ' "' + value + '"'
        cmd.append(arg)
        cmd.append(fileName)
        Log(cmd)
        retCode = subprocess.call(cmd)
        Log("changePlistInternal:" + fileName + "[" + key + ":" + value + "] = " + str(retCode))

        cmd = []
        cmd.append('/usr/libexec/PlistBuddy')
        cmd.append('-c')
        arg = 'Save'
        cmd.append(arg)
        cmd.append(fileName)
        Log(cmd)
        retCode = subprocess.call(cmd)
        Log("changePlistInternal save:" + fileName + "[" + key + ":" + value + "] = " + str(retCode))

    def changeEntitlements(self):
        appIdentifier = self.entitleIdentifier + "." + self.appleAppID #类似这样的：L4AXYWJ5X4.com.common.xiangting
        Log("Entitlement Application Identifier:" + appIdentifier)
        self.changePlistInternal(self.buildEntitlementsFile, "application-identifier", appIdentifier)

    def reCodeSign(self):
        app_full_name = os.path.join(self.buildDir + "/IOS.app")
        Log("app_full_name = " + app_full_name)
        cmd = []
        cmd.append('/usr/bin/codesign')
        cmd.append('-v')
        cmd.append('--force')
        cmd.append('--sign')
        cmd.append(self.certIdentify)
        cmd.append('--resource-rules=' + app_full_name + '/ResourceRules.plist')
        cmd.append('--entitlements')
        cmd.append(self.buildEntitlementsFile)
        cmd.append(app_full_name)
#        cmd.append('Playload/IOS.app')

        Log('reCodeSign:' + ' '.join(cmd))
        retCode = subprocess.call(cmd)
        Log("reCodeSign Result::" + str(retCode))

    def generateIPA(self):
        # 生成ipa
        Log("IOSAutoPack generateIPA")
        cmd = []
        cmd.append("xcrun")
        cmd.append("-sdk")
        cmd.append("iphoneos")
        cmd.append("PackageApplication")
        cmd.append("-v")
        cmd.append(self.buildAppDir)
        cmd.append("-o")
        cmd.append(os.path.abspath(self.targetIpaFullName))
        cmd.append("-sign")
        cmd.append(self.certIdentify)
        cmd.append("-embed")
        cmd.append(self.buildAppProvisionFile)

        Log('generate ipa:' + ' '.join(cmd))
        retCode = subprocess.call(cmd)
        Log("generateIPA Result:" + str(retCode))

    def cleanEnvironment(self):
        '''
        清理build环境
        '''
#        if os.path.exists(self.buildDir):
#            shutil.rmtree(self.buildDir)

        # 清理证书
        cmd = 'security delete-certificate -Z ' + self.certIdentify
        retCode = subprocess.call(cmd.split(' '))
        Log("security delete-keychain Result:" + str(retCode))

    def pack(self):
        self.initEnvironment()
        self.deleteOriCodeSignAndEmbedProvision()
        self.changePlist()        
        self.changeEntitlements()
        self.reCodeSign()
        self.generateIPA()
        self.cleanEnvironment()
        return 0

__global_log_file_handle = 0
def Log(content):
    if type(content) == type([0,]):
        content = str(content)
    __global_log_file_handle.write(content + "\n")
    __global_log_file_handle.flush()

if __name__ == '__main__':
    filename = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + ".txt"
    __global_log_file_handle = open(filename, "w")
    if len(sys.argv) == 0:
        Log(sys.argv)
        Log("Arguments error, please check.")
        Log("python IOSAutoPack.py  appServerURL appleAppID appDisplayName appVersion finalIPAName customerId modelId p12Pass")
        sys.exit(-1)
    else:
        Log(sys.argv)
        # appServerURL, appleAppID, appDisplayName, appVersion, finalIPAName,
        # customerId, modelId, p12Pass
        # customerId即Api接口方法中的APPID
#        packer = IOSAutoPack(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7], sys.argv[8])
        packer = IOSAutoPack("", "com.common.xiangting", "xiangting", "1.0", "AudioBook", "", "", "123123")
        packer.pack()
    __global_log_file_handle.close()   






