import sys
import requests
import os
import atexit
import time
import json
import logging
import traceback
import shutil
from PySide2.QtWidgets import *
from PySide2.QtGui import *
from PySide2.QtCore import *
from PIL import Image
from threading import Thread, enumerate
from ui_pixivtools import Ui_PixivTools
import win32api, win32con


class PicSignals_r(QObject):
    Line = Signal(QLineEdit, str)
    Pix = Signal(QLabel, QPixmap)
    Err = Signal(QMessageBox, str)


class PixivTools(QMainWindow, Ui_PixivTools):
    changeProgressBarSignal = Signal(int)

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        atexit.register(self.delete)
        atexit.register(self.delete_r)

        self.version = "release-3.1"

        self.PS = PicSignals_r()  # 实例化

        # 日志
        self.log()
        self.logger.info("导入日志模块成功")

        # 配置数据
        self.pid = "0"
        self.MultiPage = False
        self.Page = 0
        self.PicType = "png"
        self.D_PicType = "png"
        self.Mirror = True
        # self.reTry = False
        self.Remember = True
        self.r_mode = "1"
        self.img = None
        self.pidList = []
        self.Error = False
        self.fn = ""
        self.fn_r = ""
        self.esc_err = False
        self.isAutoFolder = True
        self.Progress = 0
        self.nsfw = False
        self.keyword = ""
        self.tag = []
        self.info_rd = {}

        self.picSetButtonGroup = QButtonGroup(self.groupBox_4)
        self.picSetButtonGroup.addButton(self.D_png)
        self.picSetButtonGroup.addButton(self.D_jpg)
        self.picSetButtonGroup.addButton(self.D_gif)

        # self.fileSetButtonGroup = QButtonGroup(self.groupBox_4)
        # self.fileSetButtonGroup.addButton(self.NameNo)
        # self.fileSetButtonGroup.addButton(self.NamePid)
        # self.fileSetButtonGroup.addButton(self.NameSelf)

        self.D_png.setChecked(True)
        self.editPage.setEnabled(False)
        self.SavePicture.setEnabled(False)
        self.ReloadPicture.setEnabled(False)
        self.SavePicture_R.setEnabled(False)
        self.ReloadPicture_R.setEnabled(False)
        self.Delete.setEnabled(False)
        self.FolderNameEdit.setEnabled(self.AutoFolder.isChecked())

        self.PIDSubmit.clicked.connect(self.submit)
        # self.About.clicked.connect(self.about)
        self.SavePicture.clicked.connect(self.downloadPic)
        self.ReloadPicture.clicked.connect(self.reloadPic)
        self.ResetPicture.clicked.connect(self.resetPic)
        self.isMultiPage.stateChanged.connect(self.changeMultiPage)
        self.AutoFolder.toggled.connect(self.changeFolderNameEdit)
        self.RandomButton.clicked.connect(self.random)
        self.SavePicture_R.clicked.connect(self.downloadPic_r)
        self.ResetPicture_R.clicked.connect(self.resetPic_r)
        self.ReloadPicture_R.clicked.connect(self.reloadPic_r)
        self.OpenPicture_R.clicked.connect(self.open_picture_r)
        self.Add.clicked.connect(self.addList)
        self.Clean.clicked.connect(self.clearList)
        self.Delete.clicked.connect(self.deleteList)
        self.Download.clicked.connect(self.Download_d)
        self.pictureList.itemClicked.connect(self.clickList)
        self.OpenPicture.clicked.connect(self.open_picture)
        self.changeProgressBarSignal.connect(self.changeProgressBar)

        self.About.setText(
            "pixiv工具箱\nversion {}\nhttps://github.com/Yweiwu30/PixivTools\n欢迎大家提出意见\n反馈邮箱：2046360988@qq.com\n（不定期回复）\nCopyright ©2023 0x4D2. All Rights Reserved.\n".format(
                self.version))
        self.PictureView.setText("预览图将在这里展示...")
        self.PictureView_2.setText("预览图将在这里展示...")
        self.FolderNameEdit.setText("Pixiv Download")

        self.FolderName = self.FolderNameEdit.text()

        self.label_status = QLabel(self)

        self.PS.Line.connect(self.printInfo)
        self.PS.Pix.connect(self.printPic)
        self.PS.Err.connect(self.printError)
        self.logger.info("配置数据成功")
        try:
            os.mkdir("_pixivtools_")
            os.system("attrib +h _pixivtools_")
        except FileExistsError:
            pass

        self.show()

    def log(self):
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)

        logfile = './log.txt'
        fh = logging.FileHandler(logfile, mode='a')
        fh.setLevel(logging.DEBUG)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s - %(filename)s[line:%(lineno)d][%(threadName)s, %(thread)s] - %(levelname)s: %(message)s")
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def catch_exception(func):
        def warp(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except FileNotFoundError:
                pass
            except Exception as e:
                logging.basicConfig(level=logging.WARNING,
                                    filename='./log.txt',
                                    filemode='w',
                                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')
                logging.error(f"在执行 {func.__name__}时出现错误, args: {args}, kwargs: {kwargs}")
                logging.error(traceback.format_exc())
                win32api.MessageBox(0,
                                    "程序出现错误，报错信息如下：\n{}\n程序目前可能不稳定，如遇到问题请尝试重启软件".format(
                                        e), "错误", win32con.MB_ICONERROR)

        return warp

    def printInfo(self, fd, text):
        fd.setText(text)

    def printPic(self, fd, pic):
        fd.setPixmap(pic)

    def printError(self, fd, text):
        fd.critical(self, "错误", text)

    @catch_exception
    def submit(self):  # 组合图片地址
        # self.PictureView.setText("图片获取中，这可能要一段时间")
        self.logger.info("加载网址")
        self.readInfo()
        self.disabled_sth(False)
        self.url = "https://pixiv."
        if self.Mirror:
            self.url += "re/"
        else:
            self.url += "cat/"

        self.url += str(self.pid)
        if self.MultiPage:
            self.url += "-"
            self.url += str(self.Page)
        self.url += "."
        self.url += self.PicType

        self.showPicture(self.url)

    def open_picture(self):
        if self.fn == "":
            pass
        else:
            os.startfile(os.path.abspath(self.fn))

    @catch_exception
    def disabled_sth(self, state):
        if state == False:
            # self.SavePicture.setEnabled(False)
            # self.ReloadPicture.setEnabled(False)
            self.PIDSubmit.setEnabled(False)
            self.About.setEnabled(False)
            self.isMirror.setEnabled(False)
            self.isMultiPage.setEnabled(False)
            self.editPage.setEnabled(False)
            self.editPID.setEnabled(False)
            self.pngButton.setEnabled(False)
            self.jpgButton.setEnabled(False)
            self.gifButton.setEnabled(False)
            self.isRemember.setEnabled(False)
        else:
            self.PIDSubmit.setEnabled(True)
            self.About.setEnabled(True)
            self.isMirror.setEnabled(True)
            self.isMultiPage.setEnabled(True)
            if self.MultiPage:
                self.editPage.setEnabled(True)
            else:
                self.editPage.setEnabled(False)
            self.editPID.setEnabled(True)
            self.pngButton.setEnabled(True)
            self.jpgButton.setEnabled(True)
            self.gifButton.setEnabled(True)
            self.isRemember.setEnabled(True)

    # @catch_exception
    def changeMultiPage(self):
        if self.isMultiPage.isChecked():
            self.editPage.setEnabled(True)
        else:
            self.editPage.setEnabled(False)
            self.Page = None
            self.editPage.setValue(1)

    @catch_exception
    def readInfo(self):  # 获取信息
        self.logger.info("获取图片")
        #self.statusBar.showMessage("获取信息中...")
        self.Remember = self.isRemember.isChecked()
        self.pid = self.editPID.text()  # 获取PID
        self.MultiPage = self.isMultiPage.isChecked()  # 获取是否多张插画
        if self.MultiPage:
            self.Page = self.editPage.text()  # 获取页数

        # 获取文件格式
        if self.pngButton.isChecked():
            self.PicType = "png"
        if self.jpgButton.isChecked():
            self.PicType = "jpg"
        if self.gifButton.isChecked():
            self.PicType = "gif"

        self.Mirror = self.isMirror.isChecked()  # 获取是否为镜像

    @catch_exception
    def showPicture(self, url):  # 展示图片
        #self.statusBar.showMessage("加载图片中...")  # 显示状态
        thread = Thread(target=self.requestPic, args=(url,))  # 新建线程
        self.logger.info("已新建线程")
        thread.start()
        self.logger.info("当前活跃中线程: {}".format(enumerate()))

    @catch_exception
    def requestPic(self, url):
        self.logger.info("加载图片")
        self.PS.Line.emit(self.PictureView, "加载中，请稍候...")
        try:
            self.img = requests.get(url)
            err_info = ""
            if self.img.status_code == 404:  # 检测错误状态
                if self.MultiPage:
                    err_info = "图片不存在或当前PID不是图集\nError Code: W404"
                else:
                    err_info = "图片不存在或当前PID是图集\nError Code: W404"
            elif self.img.status_code == 403:
                err_info = "服务器拒绝访问，请稍后再试\nError Code: W403"
            elif self.img.status_code == 504:
                err_info = "服务器网关超时，请稍后再试\nError Code: W504"
            elif self.img.status_code == 408:
                err_info = "服务器请求超时，请稍后再试\nError Code: W408"
            elif self.img.status_code == 503:
                err_info = "图片不存在或服务器目前无法使用\nError Code: W503"
            elif 300 <= self.img.status_code < 400:
                err_info = "服务器出现错误或已重定向到新网址，请稍后再试或联系作者\nError Code: W{}".format(
                    str(self.img.status_code))
            else:
                file_name = "_pixivtools_/{}.png".format(time.strftime(
                    "%Y%m%d%H%M%S", time.localtime()))
                self.fn = file_name
                with open(file_name, "wb") as f:
                    f.write(self.img.content)

                img4pic = Image.open(file_name)
                w = img4pic.width
                h = img4pic.height

                if w <= h:
                    scale = w / h
                    h = 420
                    w = h * scale
                else:
                    scale = h / w
                    w = 530
                    h = w * scale

                pic = QPixmap(file_name).scaled(w, h)

                self.PS.Pix.emit(self.PictureView, pic)
                # self.PictureView.setScaledContents(True)

                self.SavePicture.setEnabled(True)
                self.ReloadPicture.setEnabled(True)

                if self.Remember:
                    #self.statusBar.showMessage("保存记录中...")
                    self.logger.info("保存历史记录")
                    self.history = ""
                    localtime = time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime())

                    text = localtime + " | " + self.pid + " " * \
                           (11 - len(self.pid)) + "| " + str(self.MultiPage) + \
                           " " * (5 - len(str(self.MultiPage))) + " | "
                    if self.MultiPage:
                        text += str(self.Page)
                    try:
                        with open("History_rec.txt", "r", encoding="utf-8") as f:
                            self.history = f.read()
                    except:
                        pass

                    if self.history[0:21] == "[PIXIV_TOOLS.HISTORY]":
                        pass
                    else:
                        with open("History_rec.txt", "w", encoding="utf-8") as f:
                            f.write('''[PIXIV_TOOLS.HISTORY] 
                Time		|	 PID	| Multi | Page  \n''')

                    f = open("History_rec.txt", "a", encoding="utf-8")
                    f.write(text + "\n")
                    f.close()

        except requests.exceptions.ConnectionError:
            err_info = "连接失败"

        if err_info != "":
            self.PS.Line.emit(self.PictureView, err_info)
            self.logger.info(err_info)

        self.disabled_sth(True)
        #self.statusBar.showMessage("完成")

    @catch_exception
    def downloadPic(self):
        try:
            ft = "(*." + self.PicType + ")"
            file_path = QFileDialog.getSaveFileName(
                caption="选择文件保存位置", filter=ft)
        except:
            return
        with open(file_path[0], "wb") as f:
            f.write(self.img.content)
        QMessageBox.information(self, "提示", "文件保存成功！")
        self.logger.info("保存文件成功，文件位于{}".format(file_path[0]))

    def reloadPic(self):
        self.showPicture(self.url)

    def resetPic(self):
        self.PictureView.setText("预览图将在这里显示...")

    @catch_exception
    def delete(self):
        self.logger.info("删除缓存数据")
        shutil.rmtree("_pixivtools_", True)

    @catch_exception
    def readInfo_r(self):  # 获取信息（随机图）
        self.nsfw = self.isNsfw.isChecked()
        self.keyword = self.KeywordSearch.text()
        self.tag = self.TagSearch.text().split(",")
        if self.tag == [""]:
            self.tag = []

    @catch_exception
    def checkError_r(self, req):
        self.logger.info("检测错误")
        status = False
        self.PS.Line.emit(self.PictureView, "预览图将在这里展示..")
        if req.status_code == 404:
            self.PS.Line.emit(self.PictureView_2, "图片不存在\nError Code: R404")
        elif req.status_code == 403:
            self.PS.Line.emit(self.PictureView_2, "服务器拒绝访问，请稍后再试\nError Code: R403")
        elif req.status_code == 504:
            self.PS.Line.emit(self.PictureView_2, "服务器网关超时，请稍后再试\nError Code: R504")
        elif req.status_code == 408:
            self.PS.Line.emit(self.PictureView_2, "服务器请求超时，请稍后再试\nError Code: R408")
        elif req.status_code == 503:
            self.PS.Line.emit(self.PictureView_2, "服务器目前无法使用\nError Code: R503")
        elif 300 <= req.status_code < 400:
            self.PS.Line.emit(self.PictureView_2, "错误",
                                 "服务器出现错误或已重定向到新网址，请稍后再试或联系作者\nError Code: R{}".format(
                                     str(req.status_code)))
        else:
            status = True
        return status

    @catch_exception
    def setEnabled_r(self, stat):
        self.RandomButton.setEnabled(stat)
        self.ReloadPicture_R.setEnabled(stat)
        self.SavePicture_R.setEnabled(stat)
        self.OpenPicture_R.setEnabled(stat)
        self.isNsfw.setEnabled(stat)

    @catch_exception
    def showPicture_r(self, url):  # 展示图片
        self.logger.info("获取图片")
        self.PS.Line.emit(self.PictureView_2, "加载中，请稍候...")
        self.setEnabled_r(False)
        #self.statusBar.showMessage("获取信息中...")
        try:
            info_r = requests.get(url)

            if self.checkError_r(info_r):
                info_j = info_r.content.decode('utf8').replace("'", '"')
                self.info_rd = json.loads(info_j)
                info = self.info_rd
                # print(info, type(info))
                if info['success'] and info['data'] != None:
                    self.displayPic_r(info)
                else:
                    if info['data'] == None:
                        info['message']="没有图片信息"
                    self.PS.Line.emit(self.PictureView_2, info['message'])
                    self.logger.info(info['message'])
        except requests.exceptions.ConnectionError:
            self.PS.Line.emit(self.PictureView_2, "连接失败")
            self.logger.info("连接失败")
        #self.statusBar.showMessage("完成")
        self.setEnabled_r(True)

    def displayPic_r(self, info):
        id = str(info['data'][0]['pid'])
        title = info['data'][0]['title']
        author = info['data'][0]['author']
        tags_l = info['data'][0]['tags']
        tags = str(tags_l).replace("\'", "").replace(
            "[", "").replace("]", "")
        date_n = info['data'][0]['upload_date'] // 1000
        date = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(date_n))
        if "ai绘图" in tags:
            self.isAI.setEnabled(True)
        else:
            self.isAI.setEnabled(False)

        self.PS.Line.emit(self.name, title)
        self.PS.Line.emit(self.author, author)
        self.PS.Line.emit(self.date, date)
        self.PS.Line.emit(self.pid_r, id)
        self.PS.Line.emit(self.tagShow, tags)

        self.logger.info("加载图片")
        # self.statusBar.showMessage("加载图片中...")
        self.img_r = requests.get(info['data'][0]['url'])
        if self.checkError_r(self.img_r):
            file_name = "_pixivtools_/{}_r.png".format(time.strftime(
                "%Y%m%d%H%M%S", time.localtime()))
            self.fn_r = file_name
            with open(file_name, "wb") as f:
                f.write(self.img_r.content)
            try:
                img4pic = Image.open(file_name)
                w = img4pic.width
                h = img4pic.height

                if w <= h:
                    scale = w / h
                    h = 300
                    w = h * scale
                else:
                    scale = h / w
                    w = 510
                    h = w * scale

                pic = QPixmap(file_name).scaled(w, h)

                self.PS.Pix.emit(self.PictureView_2, pic)
            except:
                self.PS.Line.emit(self.PictureView_2, "图片加载失败")
    def reloadPic_r(self):
        self.displayPic_r(self.info_rd)

    def open_picture_r(self):
        if self.fn_r == "":
            pass
        else:
            os.startfile(os.path.abspath(self.fn_r))
    @catch_exception
    def delete_r(self):
        self.logger.info("删除缓存文件")
        try:
            os.remove(self.fn_r)
        except FileNotFoundError:
            pass
        except PermissionError:
            pass

    @catch_exception
    def downloadPic_r(self):
        try:
            ft = "(*.png)"
            file_path = QFileDialog.getSaveFileName(
                caption="选择文件保存位置", filter=ft)
        except:
            return
        with open(file_path[0], "wb") as f:
            f.write(self.img_r.content)
        QMessageBox.information(self, "提示", "文件保存成功！")
        self.logger.info("文件保存成功, 位于{}".format(file_path[0]))

    def resetPic_r(self):
        self.PictureView_2.setText("预览图将在这里显示...")

    @catch_exception
    def random(self):
        self.readInfo_r()
        self.url_r = "https://sex.nyan.xyz/api/v2/?r18={}&keyword={}".format("true" if self.nsfw else "false",
                                                                             self.keyword)
        for i in self.tag:
            self.url_r += "&tag="+i
        thread_r = Thread(target=self.showPicture_r, args=(self.url_r,))
        self.logger.info("已新建线程")
        thread_r.start()
        self.logger.info("当前活跃中线程: {}".format(enumerate()))

    def changeFolderNameEdit(self):
        self.FolderNameEdit.setEnabled(self.AutoFolder.isChecked())

    @catch_exception
    def Download_d(self):
        self.downloadBar.setValue(0)
        self.isAutoFolder = self.AutoFolder.isChecked()
        self.FolderName = self.FolderNameEdit.text()
        self.AutoFolder.setEnabled(False)
        self.FolderNameEdit.setEnabled(False)
        self.D_png.setEnabled(False)
        self.D_jpg.setEnabled(False)
        self.D_gif.setEnabled(False)
        if os.path.exists("Pixiv Download") == False:
            os.mkdir("Pixiv Download")
        if self.D_png.isChecked():
            self.D_PicType = "png"
        if self.D_jpg.isChecked():
            self.D_PicType = "jpg"
        if self.D_gif.isChecked():
            self.D_PicType = "gif"
        thread_d = Thread(target=self.dl, args=())
        self.logger.info("已新建线程")
        thread_d.start()
        self.logger.info("当前活跃中线程: {}".format(enumerate()))

    @catch_exception
    def dl(self):
        self.suc_count = 0
        self.fail_count = 0
        if self.isAutoFolder:
            try:
                os.mkdir(self.FolderName)
            except FileExistsError:
                pass
        for y in range(len(self.pidList)):
            mpid = self.pidList[y]
            self.downloadInfo.setText("({}/{})正在尝试下载图片：{}".format(y+1, len(self.pidList), mpid))
            self.Error_nf = False
            a = 2
            self.download_l(mpid, 1, a)
            if self.Error_nf == True:
                self.fail_count -= 1
                self.download_l(mpid, 0, 0)
                self.changeProgressBarSignal.emit(y)
                continue
            # self.StatusText.append("当前pid为图集")
            self.download_l(mpid, 1, 1)
            while self.Error_nf == False:
                a += 1
                # self.StatusText.append("尝试下载第{}页图片".format(a))
                self.download_l(mpid, 1, a)
            self.fail_count -= 1
            self.changeProgressBarSignal.emit(y)
        self.AutoFolder.setEnabled(True)
        self.FolderNameEdit.setEnabled(True)
        self.D_png.setEnabled(True)
        self.D_jpg.setEnabled(True)
        self.D_gif.setEnabled(True)
        self.downloadInfo.setText("下载完成，共尝试下载{}次，成功{}次，失败{}次".format(
            self.suc_count + self.fail_count, self.suc_count, self.fail_count))
        self.logger.info("下载完成，共尝试下载{}次，成功{}次，失败{}次".format(
            self.suc_count + self.fail_count, self.suc_count, self.fail_count))

    def changeProgressBar(self, y):
        self.downloadBar.setValue(100 * (y + 1) // len(self.pidList))

    @catch_exception
    def download_l(self, pid, mode, num):
        if mode == 1:
            wpid = "{}-{}".format(pid, num)
        else:
            wpid = pid
        url = "https://pixiv.re/{}.png".format(wpid)
        self.logger.info("下载链接：{}".format(url))
        self.logger.info("尝试下载图片: {}".format(wpid))
        try:
            self.img = requests.get(url)
            err_info = ""
            if self.img.status_code == 404:  # 检测错误状态
                if "-" in wpid:
                    err_info = "Error Code: W404"
                else:
                    err_info = "Error Code: W404"
                self.Error_nf = True
            elif self.img.status_code == 403:
                err_info = "服务器拒绝访问，请稍后再试\nError Code: W403"
            elif self.img.status_code == 504:
                err_info = "服务器网关超时，请稍后再试\nError Code: W504"
            elif self.img.status_code == 408:
                err_info = "服务器请求超时，请稍后再试\nError Code: W408"
            elif self.img.status_code == 503:
                err_info = "图片不存在或服务器目前无法使用\nError Code: W503"
            # self.Error_nf = True
            elif 300 <= self.img.status_code < 400:
                err_info = "服务器出现错误或已重定向到新网址，请稍后再试或联系作者\nError Code: W{}".format(
                    str(self.img.status_code))
            else:
                file_name = "{}.{}".format(wpid, self.D_PicType)
                if self.isAutoFolder:
                    path = "{}/{}".format(self.FolderName, file_name)
                else:
                    path = file_name
                with open(path, "wb") as f:
                    f.write(self.img.content)
                # self.StatusText.append("下载成功")
                self.suc_count += 1
                return
        except requests.exceptions.ConnectionError:
            pass
        self.Error = True
        # self.StatusText.append(err_info)
        self.fail_count += 1

    @catch_exception
    def clickList(self, item):
        self.Delete.setEnabled(True)
        self.logger.debug(item)
        self.clicked_item = self.pictureList.row(item)

    # print(item.text(), self.clicked_item)

    @catch_exception
    def addList(self):
        pid = self.D_pid.text()
        self.pidList.append(pid)
        self.pictureList.addItem(pid)
        self.D_pid.setText("")

    @catch_exception
    def deleteList(self):
        try:
            self.pidList.remove(self.pidList[self.clicked_item])
            self.pictureList.takeItem(self.clicked_item)
        except IndexError:
            return None
        try:
            new_selected = self.pictureList.selectedItems()[0]
            if new_selected:
                self.clicked_item = self.pictureList.row(new_selected)
        except IndexError:
            pass
        if self.pidList == []:
            self.Delete.setEnabled(False)

    @catch_exception
    def clearList(self):
        self.pidList = []
        self.pictureList.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('logo.png'))
    window = PixivTools()
    sys.exit(app.exec_())
