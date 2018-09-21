# -*- coding: utf-8 -*-
"""划分训练集、验证集"""
import os
import random
from collections import Counter
from collections import defaultdict

#classes = {'正常':'norm', '不导电':'defect1', '擦花':'defect2', '横条压凹':'defect3', '桔皮':'defect4', '漏底':'defect5', 
#'碰伤':'defect6', '起坑':'defect7', '凸粉':'defect8', '涂层开裂':'defect9', '脏点':'defect10', '其他':'defect11'}
#============输入路径dir，输出所有图片路径及标签的txt文件===============
def get_train_val_txt(filedir, save_txt):
    paths = get_folder_path(filedir)
    labels = get_folder_labels(paths)
    all_paths = []
    all_labels = []
    for i in range(len(paths)):
        _path, _label = get_path_label(paths[i], labels[i])
        all_paths.extend(_path)
        all_labels.extend(_label)
    train_path = []
    train_label = []
    val_path = []
    val_label = []
    num_class = Counter(all_labels)#得到每类的个数，dict = {0:.....}
    class_index = defaultdict(list)
    for i, item in enumerate(all_labels):
        class_index[item].append(i)#得到每类的索引，dict = {0:[0,1 ....]}
    for key, value in num_class.items():
        key_index = class_index[key]
        val_c_num = int(value*0)
        tem_a, tem_b,all_paths,all_labels = choose_val(val_c_num, key_index, all_paths, all_labels)
        val_path.extend(tem_a)
        val_label.extend(tem_b)
    for i in all_paths:
        if '' in all_paths:
            all_paths.remove('')
    for j in all_labels:
        if 100 in all_labels:
            all_labels.remove(100)
    train_path, train_label = all_paths, all_labels
    write_to_txt(train_path, train_label, save_txt[0])
    write_to_txt(val_path, val_label, save_txt[1])
def choose_val(num, total_index, all_paths, all_labels):
    path = []
    label = []
    choose_index = random.sample(total_index, num)
    for i in choose_index:
        path.append(all_paths[i])
        label.append(all_labels[i])
        all_paths[i] = ''
        all_labels[i] = 100
    return path, label, all_paths,all_labels
        
#------------------依次获取路径---------------------
#输出所有图片根目录的list
#获取绝对路径
def get_path_abs(front_dir, rela_path):
    path_abs = []
    for i in rela_path:
        i_path_abs = os.path.join(front_dir, i)
        path_abs.append(i_path_abs)
    return path_abs

#walk路径，元组转list,生成子目录列表
def walk_dir(dir_name):
    dirs = list(next(os.walk(dir_name)))[1]
    return dirs
def get_folder_path(filedir):
    path = [] 

#遍历root1/guangdong_round1...
    dirs1 = walk_dir(filedir)
    dirs1 = get_path_abs(filedir, dirs1)
#遍历root2(dirs1)/瑕疵，无瑕疵
    dirs2 = []
    for _dirs in dirs1:
        dirs_2 = walk_dir(_dirs)
        if dirs_2 == []:
            path.append(_dirs)
        else:
        #获取三级目录的绝对路径
            dirs_2 = get_path_abs(_dirs, dirs_2)
            dirs2.extend(dirs_2)
#遍历root3(dirs2)/三级目录
    for __dirs in dirs2:
        dirs_3 = walk_dir(__dirs)
        if dirs_3 == []:
            path.append(__dirs)
        #遍历四级根目录/其它
        else:
            dirs_3 = get_path_abs(__dirs, dirs_3)
            path.extend(dirs_3)            
    return path
#----------------获取path对应的labels的list-----------------------
def get_folder_labels(path_name):
    labels = []
    for item in path_name:
        if "无瑕疵样本" in item:
                labels.append(0)
        else:
            if "不导电" in item:
                labels.append(1)
            elif "擦花" in item:
                labels.append(2)
            elif "横条压凹" in item:
                labels.append(3)
            elif "桔皮" in item:
                labels.append(4)
            elif "漏底" in item:
                labels.append(5)
            elif "碰伤" in item:
                labels.append(6)
            elif "起坑" in item:
                labels.append(7)
            elif "凸粉" in item:
                labels.append(8)
            elif "涂层开裂" in item:
                labels.append(9)
            elif "脏点" in item:
                labels.append(10)
            elif "其他" in item:
                labels.append(11)
    return labels
#获得所有图片路径和标签
def get_path_label(folder_name, folder_label):
    ImageList = []
    Label=[]
    def getAllimages(folder):
        assert os.path.exists(folder)
        assert os.path.isdir(folder)
        imageList = os.listdir(folder)
        _list = []
        for item in imageList:
            if 'jpg' in item:
                _list.append(os.path.join(folder, item))
        return _list
    ImageList.extend(getAllimages(folder_name))
    for i in range(len(ImageList)):
        Label1 = folder_label
        Label.append(Label1)

    return ImageList, Label
#-------------路径及标签写入txt文件并保存---------------
def write_to_txt(img_path, img_labels, file_path):
    fp = open(file_path, "w+")
    _list = []
    for i in range(len(img_path)):
        _list.append(img_path[i] + '\t' + str(img_labels[i]))
    for i in range(len(_list)):
        s = str(_list[i]).replace('[','').replace(']','')#去除[],这两行按数据不同，可以选择
        s = s.replace("'",'').replace(',','') +'\n'   #去除单引号，逗号，每行末尾追加换行符
        fp.write(s)
    fp.close()
    
if __name__ == '__main__':
    data_dir = 'G:/exercise/201809-tc-lv/lv-chusai/guangdong_round1_train2_20180916'
    save_txt = ['train.txt', 'val.txt']
    get_train_val_txt(data_dir, save_txt)
