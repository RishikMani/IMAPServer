import pyqtgraph as pg
import numpy as np
import pandas as pd
import os
import getpass
import email
import imaplib
import math
import pickle
import sys
import datetime
import gc
from shutil import copyfile
from pyqtgraph.Qt import QtCore, QtGui
from numpy import array, ones, linspace, conjugate
from cmath import pi, exp
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QLabel, QSlider, QWidget
from PyQt5.QtCore import Qt

##################################
# Configurations
##################################

# A 7 column panda dataset to hold the details of an email
# The column index contains the index number of the email in the panda dataset,
# and the column Mail_Size contains the size of email in kilobytes.
columns = ["Index", "Subject", "From", "To", "Date", "Attachment", "Mail_Path",
           "Mail_Size"]

# user = "thermann"  # username
user = "rmani"  # username
imap_server_name = "imap.techfak.uni-bielefeld.de"

# path of the csv file containing the panda dataset. It contains the details
# of the emails.
# dataset_path = r"D:\Bielefeld\Individual Project\DataFrame.csv"
data_path = r"./data"

try:
    os.makedirs(data_path)
except:
    print('directory {} already exists'.format(data_path))

dataset_path = data_path + "/DataFrame.csv"

# path of the pickle dataset. It contains the details of the nodes in the H2
# graph.
# pickle_dataset_path = r"D:\Bielefeld\Individual Project\TreeDataFrame.pkl"
pickle_dataset_path = data_path + "/TreeDataFrame.pkl"


class Graph(pg.GraphItem):
    """
    Class defining various overloaded methods for scatter plot graph
    """

    def __init__(self):
        """
        Method to initialize the graph
        """

        self.dragPoint = None
        self.dragOffset = None
        self.textItems = []
        pg.GraphItem.__init__(self)
        self.scatter.sigClicked.connect(self.onclick)
        self.data = lambda x: None
        self.text = lambda x: None
        self.current_node_positions = dict()
        self.new_center_node = None

    def setData(self, **kwds):
        self.text = kwds.pop("text", [])
        self.data = kwds
        if "pos" in self.data:
            npts = len(self.data["pos"])
            self.data["data"] = np.empty(npts, dtype=[("index", int)])
            self.data["data"]["index"] = np.arange(npts)
        self.settexts(self.text)
        self.updategraph()

    def settexts(self, text):
        """
        Method to set the labels of the nodes in the H2 tree graph.

        Knowledge arguments:
        text: The label to be set for all nodes in the graph
        """

        for i in self.textItems:
            i.scene().removeItem(i)
        self.textItems = []
        for t in text:
            item = pg.TextItem(t)
            self.textItems.append(item)
            item.setParentItem(self)

    def updategraph(self):
        pg.GraphItem.setData(self, **self.data)
        for i, item in enumerate(self.textItems):
            item.setPos(*self.data["pos"][i])

    def mouseDragEvent(self, ev):
        """
        Click and hold on a node to drag a node to any position.

        Knowledge arguments:
        ev: event value
        """

        if ev.button() != QtCore.Qt.LeftButton:
            ev.ignore()
            return

        if ev.isStart():
            # We are already one step into the drag.
            # Find the point(s) at the mouse cursor when the button was first
            # pressed.
            pos = ev.buttonDownPos()
            pts = self.scatter.pointsAt(pos)
            if len(pts) == 0:
                ev.ignore()
                return
            self.dragPoint = pts[0]
            ind = pts[0].data()[0]
            self.dragOffset = self.data["pos"][ind] - pos
        elif ev.isFinish():
            self.dragPoint = None
            return
        else:
            if self.dragPoint is None:
                ev.ignore()
                return

        ind = self.dragPoint.data()[0]
        self.data["pos"][ind] = ev.pos() + self.dragOffset
        self.updategraph()
        ev.accept()

    def onclick(self, plot):
        # Once a node on the graph is clicked, the node should be repositioned
        # to the center of the graph
        x = 0
        y = 0
        
        # position of the clicked point
        x, y = plot.ptsClicked[0]._data[0], plot.ptsClicked[0]._data[1]

        for node in H2Tree.pickle_dataset:
            # When a node in the graph has been clicked, the graph would
            # reposition.
            # When the graph repositions, the old position would be overwritten
            # by new positions.
            # So save the old positions in the form of a dictionary.
            self.current_node_positions[node.number] = node.position

            # based on the (x, y) coordinates of the clicked node, find out
            # which node has been clicked upon.
            if node.position == (x, y):
                self.new_center_node = node

        # for the new centre node, re-hyperbolize the tree and render the new
        # tree graph.
        h2_tree.operation_on_h2_tree(self.new_center_node, 
                                     self.current_node_positions)


class Node:
    """
    A class defining the structure of the tree node and its related properties
    """

    count = 0  # to maintain the count of nodes in the graph

    def __init__(self, parent=None, depth=0, name=None):
        """
        Method to set the various properties useful for the class

        Knowledge arguments:
        parent: Parent node
        depth: the depth of the new node
        name: the label of the node
        """
        
        # with every node created, increment the total number of nodes by 1
        Node.count += 1
        self.parent = parent  # to maintain the parent nodes of any node
        self.children = []  # to maintain the child nodes of any node

        # to maintain the overall depth of the tree at subsequent hierarchy
        # levels
        self.depth = depth
        
        # the label of the node to be used for labelling purpose
        self.name = name
        
        self.number = Node.count  # the index of the node created
        self.isMail = False  # to check if the node is an Email or a directory
        self.mailID = 0  # index number of the mail in DataFrame.csv
        
        # to hold the size of all mails directly under one directory
        self.mailSize = 0.0
        
        # to hold the total number of mails within a directory
        self.numberOfMails = 0

        # timestamp to hold the most recent mail timestamp within a directory
        self.timestamp = None
        
        # to hold the 2D position of any node after hyperbolize
        self.position = []
        self.max_depth = 0

    def getmaxdepth(self):
        """
        Method to return the maximum depth of the tree graph

        :return: The maximum depth of the tree
        """

        if self.max_depth < self.depth:
            self.max_depth = self.depth
            return self.max_depth


class Q_Slider(QtGui.QSlider):
    def mousePressEvent(self, event):
        QtGui.QSlider.mousePressEvent(self, event)
        opt = QtGui.QStyleOptionSlider()
        self.initStyleOption(opt)
        gr = self.style().subControlRect(QtGui.QStyle.CC_Slider, opt, 
                       QtGui.QStyle.SC_SliderGroove, self)
        sr = self.style().subControlRect(QtGui.QStyle.CC_Slider, opt, 
                       QtGui.QStyle.SC_SliderHandle, self)
        if self.orientation() == QtCore.Qt.Horizontal:
            pos = event.pos().x()
            sliderLength = sr.width()
            sliderMin = gr.x()
            sliderMax = gr.right() - sliderLength + 1
        else:
            pos = event.pos().y()
            sliderLength = sr.height()
            sliderMin = gr.y()
            sliderMax = gr.bottom() - sliderLength + 1
        value = QtGui.QStyle.sliderValueFromPosition(self.minimum(), 
                                                     self.maximum(),
                                                     pos - sliderMin, 
                                                     sliderMax - sliderMin, 
                                                     opt.upsideDown)
        if value != self.value():
            self.setValue(value)


class Slider(QWidget):
    """
    A class to create an instance of the slider on the graph.
    Sliding the slider will result in filtering the nodes on the basis of their
    year of being received
    """

    def __init__(self, minimum, maximum, sl_adjacency_list, sl_node_text, 
                 sl_graph, sl_node_size, sl_lines, sl_parent=None):
        """
        Method to set the various properties useful for the class

        Knowledge arguments:
        minimum: the minimum value of the slider
        maximum: the maximum value of the slider
        sl_adjacency_list: the adjacency list of the graph
        sl_node_text: list containing the labels of the nodes
        sl_graph: current instance of the graph
        sl_node_size: list containing the sizes of the nodes
        sl_lines: list containing the line styles of various connections 
                  between the nodes
        sl_parent: the parent graphic window
        """

        super(Slider, self).__init__(parent=sl_parent)
        layout = QtGui.QGridLayout(self)
        self.sl = QSlider(Qt.Vertical)
        self.sl.setMinimum(minimum)
        self.sl.setMaximum(maximum)
        self.sl.setValue(minimum)
        self.sl.setTickPosition(QSlider.TicksLeft)
        self.sl.setTickInterval(1)
        self.sl.setSingleStep(1)
        self.node_colors = []
        self.adjacency_list = sl_adjacency_list
        self.nodeText = sl_node_text
        self.positions = []
        self.g = sl_graph
        self.node_size = sl_node_size
        self.lines = sl_lines

        # connecting the value changed on the slider with an event
        self.sl.valueChanged.connect(self.valuechange)

        for index, value in enumerate(range(maximum, minimum - 1, -1)):
            label = QLabel("{}".format(value))
            layout.addWidget(label, index, 0, QtCore.Qt.AlignLeft)

        layout.addWidget(self.sl, 0, 1, maximum - minimum + 1, 1, 
                         QtCore.Qt.AlignLeft)

    def valuechange(self):
        """
        On changing the value using slider, mails whose year of receipt would 
        be same as the selected value would lit up green in color while rest of
        the nodes would turn red
        """

        year = self.sl.value()  # the value of the item chosen on the slider
        self.positions = []
        self.node_colors = []

        # Check every node from the pickle dataset, if the year of the mail is
        # equal to the item chosen on the slider, then turn the node green and
        # rest of the node as blue
        for node in h2_tree.pickle_dataset:
            self.positions.append(node.position)
            if node.isMail and node.timestamp.year == year:
                self.node_colors.append('g')
            else:
                self.node_colors.append('r')

        # set the data of the graph and render the graph once again
        self.g.setData(pos=np.array(self.positions), 
                       adj=np.array(self.adjacency_list), 
                       size=self.node_size,
                       pxMode=False, 
                       text=self.nodeText, 
                       pen=self.lines, 
                       brush=self.node_colors)


class Widget(QWidget):
    """
    A class to create a widget on the graph
    """

    def __init__(self, w_latest_timestamp, w_oldest_timestamp, 
                 w_adjacency_list, w_nodetext, w_graph, w_node_size,
                 w_lines, w_parent=None):
        """
        Method to set the various properties useful for the class

        Knowledge arguments:
        w_latest_timestamp: the latest year of all the mails observed in the 
                            mail box
        w_oldest_timestamp: the oldest year of all the mails observed in the 
                            mail box
        w_adjacency_list: the adjacency list of the nodes in the H2 tree graph
        w_nodetext: list containing the labels of the nodes in the H2 tree 
                    graphs
        w_graph: the instance of the graph created
        w_node_size: a list containing the sizes of the nodes in the H2 tree 
                     graph
        w_lines: an ndarray containing the width of lines connecting nodes in 
                 H2 tree graph
        w_parent: the instance of the parent of the graphic window
        """

        super(Widget, self).__init__(parent=w_parent)
        self.horizontalLayout = QHBoxLayout(self)
        self.w1 = Slider(w_oldest_timestamp, w_latest_timestamp, 
                         w_adjacency_list, w_nodetext, w_graph, w_node_size,
                         w_lines, w_parent)
        self.horizontalLayout.addWidget(self.w1)


class Login:
    """
    Login class consists of the methods that are required to login to the 
    server.
    """

    def __init__(self, server_name, l_user):
        """
        Method to set the various properties useful for the class

        Knowledge arguments:
        server_name: URL of the IMAP server
        l_user: username
        """
        
        # creates a connection over SSL encrypted socket
        self.svr_obj = imaplib.IMAP4_SSL(server_name)
        
        pwd = self.get_credentials()  # retrieve user's login password

        # Check if the login was successful or was denied.
        if self.svr_obj.login(user=l_user, password=pwd):
            print("User " + user + " logged in successfully.")
        else:
            print("Login for the user " + user + " was denied. Please check \
                  your credentials.")

    @staticmethod
    def get_credentials():
        """
        Gets the password of the user

        :return:  password typed on the terminal
        """

        # The method echoes password when run using PyCharm.
        # Please use windows CMD to run the script so as not to echo the
        # password or built-in terminal from PyCharm.
        # Or use Terminal inside PyCharm to run the code.
        pwd = getpass.getpass("Enter the password: ", stream=None)
        return pwd


class ImapParse:
    """
    Class that defines all the methods required to parse an IMAP server
    """

    # The years obtained would be used for the first and the last tick on the
    # widget respectively.
    latestYear = None
    oldestYear = None

    def __init__(self, ip_svr, ip_root, ip_index, ip_columns, ip_dataset_path, 
                 ip_nodetext, ip_month_dict, ip_pickle_dataframe_list):
        """
        Method to set the various properties useful for the class

        Knowledge arguments
        ip_svr: IMAP server object obtained for SSL encrypted connection
        ip_root: root node of the H@ tree graph
        ip_index: the index number of the panda dataset row
        ip_columns: list of the columns in the panda dataset
        ip_dataset_path: the local system path where panda dataset would be 
                         written
        ip_nodetext: list containing the names of the nodes to be displayed 
                     when the tree graph is rendered
        ip_month_dict: dictionary to help to convert the month names to their 
                       respective calendar month numbers
        ip_pickle_dataframe_list: a list containing the nodes of the tree graph
        """

        self.svr = ip_svr  # variable to hold the server object
        self.root = ip_root  # to hold the root node of the H2 tree
        
        # to hold the index of the items in the panda dataset
        self.index = ip_index

        # holds the list of columns that would be populated in panda dataset
        self.columns = ip_columns
        
        # holds the path of the dataset on the local system
        self.dataset_path = ip_dataset_path
        
        # holds the list of the labels for the nodes in H2 tree graph
        self.nodeText = ip_nodetext

        # a dictionary holding the month and month number for timestamp
        # conversion
        self.month_dict = ip_month_dict
        
        # list to contain the directories directly under root directory /
        self.root_directories = []
        
        # list containing all node objects from H2 tree graph
        self.pickle_dataframe_list = ip_pickle_dataframe_list

        # instance of the class ImapTree
        self.imap_tree = ImapTree(self.nodeText, self.pickle_dataframe_list, 
                                  adjacency_list)
        
        # flag to check whether the call is for synchronization or not
        self.sync = False
        
        self.max_depth = 0  # holds the maximum depth of the H2 tree graph
        self.node_dict = dict()

    def parse_server(self, sync):
        """
        The function starts from the root directories of the IMAP server.
        For every directory it checks whether there any mails to download.
        It also checks whether there are children directories of the current 
        selected directory.

        Knowledge arguments:
        sync: a flag to decide whether the request is for the first time or to 
        synchronize with the server
        """

        try:
            self.sync = sync
            child = None  # holds the list of all children of the root directories
            self.svr.select("inbox", readonly=False)

            # If the call is not for synchronization, then fetch details from the
            # server and add children to the root node.
            if not self.sync:
                # lists all the directories present on the server
                test, directories = self.svr.list('""', "*")

                for mbox in directories:
                    # get the name of the directories
                    flags, separator, name = self.parse_mailbox(bytes.decode(mbox))

                    # To recursively parse through the server we only need
                    # directories directly under '/'.
                    # e.g INBOX, Sent, Deleted Items are directories immediately
                    # under '/' but INBOX/ISYProject
                    # e.g. Folder1/Subdirectory/, here we only need to store Folder1
                    # for recursive parsing.
                    if len(name.split('/')) > 1:
                        continue
                    else:
                        self.root_directories.append(name)

                # If you do not want to process any particular directory for any
                # reason, then remove them from the root_directories list.
                # self.root_directories.remove('Calendar')
                # self.root_directories.remove('Contacts')
                # self.root_directories.remove('Journal')
                # self.root_directories.remove('Notes')
                # self.root_directories.remove('RSS Subscriptions')
                # self.root_directories.remove('Sync Issues')
                # self.root_directories.remove('Tasks')

                # The approach is to start from the root node directories and process
                # one level of directory at a time.
                # Starting from the root nodes, we will first create nodes for root
                # directories. e.g. INBOX, Sent, etc.
                # For every directory in the 'root_directories', add a new node and
                # set 'root' as its parent.
                for directory in self.root_directories:
                    # adds a new node to the H2 tree graph
                    child, self.max_depth = self.imap_tree.grow(self.root,
                                                                directory)

                # Root directories have a level of 1.
                # Once root directories have been added to the graph as nodes,
                # process their sub-directories.
                # e.g. once /Folder1 has been added at level 1, then add
                # /Folder1/ChildFolder1
                if self.root.children:
                    self.parse_child_nodes(self.root.children)

            else:
                # else if the call is for synchronization, then load the pickle
                # dataset first.
                # Then for every new mail on the server, add a new node to the
                # H2 tree.

                # load the contents of the stored pickle dataset into a list
                self.pickle_dataframe_list = []

                # list to store the labels of the nodes in the H2 tree graph
                self.nodeText = []

                _pickle_dataset = PickleDataset()

                # load the data from the pickle dataset
                content = _pickle_dataset.get_pickle_dataset()

                # list to hold the rest of directories, e.g.
                # Folder1/ChildFolder1
                not_root_directories = []

                for node in content:
                    if self.max_depth < node.depth:
                        # store the maximum depth of the tree.
                        # his value would be used further while rendering the stored
                        # tree in the form of pickle dataset.
                        self.max_depth = node.depth

                    # Fetch one node at a time from the pickle dataset and store it
                    # in a dictionary.
                    # This dictionary would further be used to iterate through the
                    # nodes to render the tree saved in memory.
                    self.node_dict[node.name] = node

                    self.pickle_dataframe_list.append(node)

                    # add the name of the node for the node labels
                    self.nodeText.append(node.name)

                    # Start from the Root node and then traverse through
                    # sub-directories to put the new mails under the correct
                    # directory
                    if node.name == "Root":
                        self.root_directories = node.children

                    else:
                        # if the node is not 'Root', then make the node adjacent
                        # with it's parent node
                        adjacency_list.append(
                            (node.parent.number - 1, node.number - 1)
                        )

                        # Further, there are some more directories, e.g.
                        # Folder1/ChildFolder1/...,
                        # which are not root directories. These subdirectories also
                        # needed to be checked
                        # for any recent changes on the server during the
                        # synchronization call.
                        if not node.isMail and node not in self.root_directories:
                            not_root_directories.append(node)

                    # Get the range of the values to be displayed as the tick
                    # labels on the slider
                    if node.timestamp is not None:
                        self.get_timestamp_range(node.timestamp.year)

                self.imap_tree = ImapTree(self.nodeText, self.pickle_dataframe_list,
                                          adjacency_list)

                # list containing all the directories on the IMAP server
                directories = self.root_directories + not_root_directories

                # check all the directories for recent changes
                for node in directories:
                    # date is of pattern Sun, 07 Jan 2018 22:14:19 +0100

                    # get the latest timestamp of the directory
                    date = self.get_latest_timestamp(node)

                    if date == "No mail exists":
                        print("No mail exists in the directory " + node.name + ".")
                        continue
                    else:
                        print("The timestamp of " + node.name + " is " + date + ".")

                    # convert the date string to datetime format
                    date = self.get_converted_timestamp(date)

                    # Convert the date from the timestamp to an integer and then
                    # compare. If the timestamp is bigger than the one stored in the
                    # pickle, it implies new mail has arrived in the directory.
                    if date > node.timestamp:
                        print("New mails found in " + node.name + " since last \
                              login.")
                        self.check_emails_for_sync(node, date)
                    else:
                        print("There are no new mails in " + node.name +
                              " to be synced.")
                return
        except Exception as ex:
            print("The following error happened in parse_server: \n")
            print(ex)

    @staticmethod
    def parse_mailbox(data):
        """
        Custom method to get the name of the directories
        """

        flags, b, c = data.partition(" ")
        separator, b, name = c.partition(" ")
        return flags, separator.replace('"', ""), name.replace('"', "")

    def parse_child_nodes(self, parent_nodes):
        """
        The function takes a list of nodes at any particular level
        and then checks for sub-directories.
        The directories are also checked for mails.

        Keyword arguments:
        parent_nodes: list of nodes which will be checked for any child 
                      directories or mails
        """
        
        ignore_directories = ["INBOX/Ignore"]
        
        # a list to hold the children of nodes in list parent_nodes
        child_nodes = []
        
        for node in parent_nodes:
            # If the node is of type directory then check for Emails.
            if not node.isMail:
                self.check_for_emails(node)

                # Check for sub-directories inside the directory
                test, directories = self.svr.list('""', '"' + node.name + '/*"')
                if all(x is not None for x in directories):
                    for mbox in directories:
                        flags, separator, _name = \
                            self.parse_mailbox(bytes.decode(mbox))

                        # Consider only the immediate sub-directories as we
                        # go one level at a time
                        if self.if_immediate_child(_name, node.name) and \
                                (_name not in ignore_directories):
                            child, self.max_depth = \
                                self.imap_tree.grow(node, _name)
                            child_nodes.append(child)

        # Once all the immediate sub-directories have been added, we now need
        # to process them.
        if child_nodes:
            self.parse_child_nodes(child_nodes)
        return

    def get_latest_timestamp(self, node):
        """
        Method to get the latest timestamp of a subdirectory during 
        synchronization call

        Keyword arguments:
        node: the directory whose timestamp on server has to be checked

        :return: the date of the email
        """

        print("Getting the latest timestamp of directory " + node.name + ".")

        num = self.svr.select('"' + node.name + '"', readonly=False)

        # During synchronization, mails could not be sorted in descending order.
        # Fetching the list of mail comes in ascending form.
        # The most recent mail at the end of the list, and the most old at the
        # top of the list.
        resp, lst = self.svr.fetch(num[1][0].decode("utf-8"), "(RFC822)")

        if resp == "OK":
            email_message = email.message_from_bytes(lst[0][1])
            return email_message["Date"]

        # if the subdirectory is empty and has no mails return a definite
        # string
        return "No mail exists"

    def check_emails_for_sync(self, node, date):
        """
        During synchronization, if any directory has new mails, then download 
        the mail details

        Keyword arguments:
        node: the directory which needs to be synced
        date: the latest timestamp of the directory
        """

        print('Syncing the directory ' + node.name + '.')
        self.svr.select('"' + node.name + '"', readonly=False)

        timestamp = None

        # To search the mail from a particular directory from a particular date,
        # we need the date to be of form DD-MMM-YYYY (e.g. 10-May-2018).
        # Currently the date comes in the format '26 Nov 2017 16:41:25 +0100'.
        # We need to convert the date into form 26-Nov-2017
        for key in month_dict.keys():
            if date.month == int(month_dict[key]):
                timestamp = str(date.day) + '-' + key + '-' + str(date.year)
                break

        # get the list of mails from a directory since a particular date, the
        # most recent would be at the bottom
        rv, data = self.svr.search(None, "SINCE", timestamp, "ALL")
        self.get_mail(node, data)

    def check_for_emails(self, node):
        """
        The method checks for emails under a particular directory

        Keyword arguments:
        node: directory in the form of node structure under which mails need to
              be checked
        """

        print(" Checking and downloading emails from the directory " +
              node.name + ".")

        # While reading any directory, 'readonly' flag has been set False
        # so that the UNSEEN status of mails do get changed.
        # If the status does not get changed the same mail would be fetched
        # again during the synchronization call
        self.svr.select('"' + node.name + '"', readonly=False)

        # Get the list of the mails in descending order,
        # so that the most recent mail is at the top and then take timestamp of
        # the most recent mail.
        rv, data = self.svr.sort("REVERSE DATE", "UTF-8", "ALL")
        self.get_mail(node, data)

    @staticmethod
    def if_immediate_child(child, parent):
        """
        The method checks if the directories under parent are immediate 
        sub-directories or not

        Keyword arguments:
        child: sub-directory
        parent: parent directory

        :return: True or false
        """

        length = len(parent)  # if parent directory is 'A', then
        child = child[length + 1:]  # A/B, A/B/C, A/B/C/D will be B, B/C, B/C/D

        # We split on char '/', if length is more than 1, e.g. in A/B, A/B/C,
        # we reject A/B/C.
        # This way only the sub-directory B gets approved which is immediate
        # sub-directory of A.
        if len(child.split('/')) > 1:
            return False
        else:
            return True

    def get_mail(self, node, data):
        """
        Downloads the mail present under a given directory on the IMAP server

        Keyword arguments:
        node: directory from which mails should be downloaded
        data: the data obtained from the IMAP server
        """

        try:
            # flag to check whether the mail being referred to is the latest or not
            recent_mail = True
            mails_processed = 0

            # During synchronization when a new record was getting inserted the
            # index of the new item always turned out 1.
            # To fix the issue, first we read the maximum value of the column
            # 'Index'. The new index thus would be the returned value of the
            # Index + 1.
            if self.sync:
                pd_dataframe = pd.read_csv(self.dataset_path, error_bad_lines=False,
                                           encoding="latin-1")
                self.index = max(pd_dataframe["Index"].values) + 1
                del pd_dataframe
                gc.collect()

            for num in data[0].split():
                mails_processed = mails_processed + 1

                # get the content of the email
                resp, lst = self.svr.fetch(num, "(RFC822)")

                # Check if the response to fetch command was successful or not, if
                # not raise exception and abort
                if resp != "OK":
                    raise Exception("Bad response: %s %s" % (resp, lst))

                # get the size of the mail in bytes
                mail_size = self.get_mail_size(num)

                # converting mail_size to kilobytes
                mail_size = "{0:.2f}".format(float(mail_size) / 1024)

                body = lst[0][1]
                email_message = email.message_from_bytes(body)

                if self.sync and \
                        self.get_converted_timestamp(email_message["Date"]) \
                        <= node.timestamp:
                    continue

                # if the email has any attachment, then get the name
                attachment_name = self.get_attachment(email_message)

                # fields to be downloaded from the email
                fields = [[self.index, email_message["Subject"],
                           email_message["From"], email_message["To"],
                           email_message["Date"], attachment_name, node.name,
                           mail_size]]

                # Create a panda dataframe
                df = pd.DataFrame(data=fields, columns=self.columns)

                # If the file does not exist, then create the new file,
                # else append the panda dataframe to the CSV file.
                if not os.path.isfile(self.dataset_path):
                    df.to_csv(path_or_buf=self.dataset_path, sep=',', header=True,
                              index=False)
                else:
                    with open(self.dataset_path, 'a', encoding="utf-8") as f:
                        df.to_csv(f, header=False, index=False)

                self.index = self.index + 1  # index of the panda dataframe items

                # for every mail downloaded add a new node to the tree graph
                child, self.max_depth = self.imap_tree.grow(node,
                                                            email_message["Date"],
                                                            True,
                                                            self.sync)

                # for mails set the node label as the date when the mail was
                # received
                self.nodeText.append(email_message["Date"][0:16])

                child.mailSize = float(mail_size)

                # set the timestamp of the child node
                child.timestamp = \
                    self.get_converted_timestamp(email_message["Date"])

                if recent_mail and not self.sync:
                    node.timestamp = \
                        self.get_converted_timestamp(email_message["Date"])

                elif mails_processed == len(data[0].split()) and self.sync:
                    # During synchronization mails cannot be sorted out in
                    # descending order of date.
                    # Hence, the last mail in the list would be the latest email.
                    # So the latest timestamp of the node should be the timestamp of
                    # the latest email as well.
                    # mails_processed is a counter of the number of mails that have
                    # been processed in a directory.
                    # e.g. if we have 10 mails in the directory, then the mail at
                    # position 10 would have the latest timestamp
                    # So when the counter turns 10 we would know we have reached the
                    # latest mail, and thus assign timestamp.
                    node.timestamp = \
                        self.get_converted_timestamp(email_message["Date"])

                self.get_timestamp_range(child.timestamp.year)

                recent_mail = False
        except Exception as ex:
            print("An exception occurred in get_mail.")
            print(ex)

    def get_mail_size(self, num):
        """
        Function to get the size of the mail

        Keyword arguments:
        num: unique mail identifier

        :return: size of the email in kilobytes
        """

        # RFC822.SIZE is the default operator to get the size of mails
        resp, lst = self.svr.fetch(num, "(RFC822.SIZE)")
        
        # convert the byte array into string array
        byte_array = lst[-1].decode("utf-8")
        
        # the size of mail is stored after the last whitespace in array
        last_whitespace_index = byte_array.rfind(" ")
        return lst[-1].decode("utf-8")[
               last_whitespace_index - len(byte_array) + 1:-1
            ]

    @staticmethod
    def get_attachment(email_message):
        """
        Downloads the attachment names in an email, if any

        Keyword arguments:
        email_message: email obtained from the IMAP server

        :return: list of the attachments in an email
        """

        attachments = []  # an empty list to contain the name of attachments

        for part in email_message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get("Content-Disposition") is None:
                continue

            filename = part.get_filename()  # get the name of the attachment
            if filename is not None:
                # append the name of the attachment to the list
                attachments.append(filename)

        if not attachments:
            return "No attachment"  # default message if there is no attachment
        else:
            return attachments

    def get_converted_timestamp(self, date):
        """
        Converts the date when an email was received to a number format

        Keyword arguments:
        date: date of receiving of an email

        :return: the timestamp of the email in datetime format
        """

        # Date string is of the format 'Sun, 26 Nov 2017 16:41:25 +0100'
        # We will slice the string to store date+time as the timestamp
        timestamp = date[5:25]  # would return a value '26 Nov 2017 16:41:25'

        # removes all spaces and ':'
        for ch in [' ', ':']:
            timestamp = timestamp.replace(ch, "")

        # for days 1 to 9 of any month pad an extra 0 at the start of the string
        if len(timestamp) < 15:
            timestamp = '0' + timestamp

        # convert the date string into an integer, so that Date operations can
        # be performed on it.
        timestamp = timestamp[0:2] + self.month_dict[timestamp[2:5]] + \
        timestamp[5:]

        # Convert the timestamp string obtained from the server to a DatTime
        # format.
        timestamp = datetime.datetime(
            int(timestamp[4:8]), int(timestamp[2:4]),
            int(timestamp[:2]), int(timestamp[8:10]),
            int(timestamp[10:12]), int(timestamp[12:])
        )
        return timestamp

    @staticmethod
    def get_timestamp_range(year):
        """
        This method retrieves the maximum and minimum year from the mail boxes.
        The values retrieved would be used as the tick labels on the slider 
        widget.

        Knowledge arguments:
        :param year: the year in which the mail was received
        """

        # Retrieve the year in which the most recent mail of the mailbox was
        # received
        if ImapParse.latestYear is None:
            ImapParse.latestYear = year
        else:
            if ImapParse.latestYear < year:
                ImapParse.latestYear = year

        # Retrieve the year in which the most oldest mail of the mailbox was
        # received
        if ImapParse.oldestYear is None:
            ImapParse.oldestYear = year
        else:
            if ImapParse.oldestYear > year:
                ImapParse.oldestYear = year


class PickleDataset:
    """
    A class that contains methods to load and dump pickle dataset
    """

    def get_pickle_dataset(self):
        """
        Loads the pickle dataset from the file system

        :return: content of the file read from the local drive
        """
        with open(pickle_dataset_path, "rb") as file:
            content = pickle.load(file)
            file.close()
        return content

    def dump_pickle_dataset(self, dpd_pickle_dataframe):
        """
        A method to dump the pickle dataset

        Keyword arguments:
        :param dpd_pickle_dataframe: a list containing the nodes of the H2 tree
                                     graph
        """
        with open(pickle_dataset_path, 'wb') as file:
            pickle.dump(dpd_pickle_dataframe, file)
            file.close()


class ImapTree:
    def __init__(self, it_nodetext, it_pickle_dataframe_list, 
                 it_adjacency_list):
        """
        Method to initialize properties for the class

        Keyword arguments:
        it_nodetext: a list containing the label of the nodes
        it_pickle_dataframe_list: a list containing node objects from the H2 
                                  tree graph
        it_adjacency_list: a list defining the adjacency of nodes in the H2 
                           tree graph
        """
        self.nodeText = it_nodetext
        self.pickle_dataframe_list = it_pickle_dataframe_list
        self.adjacency_list = it_adjacency_list
        self.max_depth = 0

    def grow(self, node, directory, ismailnode=False, sync=False):
        """
        Method to add a new node in the H2 tree graph

        Keyword arguments:
        node: node to which a child needs to be added
        directory: name of the directory or the label of a mail
        ismailnode: if the new node being added represents a mail or a 
                    directory on the IMAP server
        sync: A flag to check whether the call is for synchronization or not
        :return: the child node currently added along with the maximum depth of
                 the tree
        """

        child = Node(node, node.depth + 1, directory)  # create a child node
        self.max_depth = child.getmaxdepth()  # get the max depth of the tree

        if ismailnode:
            # if the node is of mail type then set the property as True
            child.isMail = ismailnode

        # if the call is for synchronization
        if sync:
            # pickle_dataframe consists of all the nodes loaded from the pickle
            # dataset. A new node addition means the number of the new node
            # should be the length of the list incremented by 1.
            child.number = len(self.pickle_dataframe_list) + 1
            
        # add the child to parent node's child list
        node.children.append(child)

        # setup an adjacent connection between the child and parent node
        self.adjacency_list.append([node.number - 1, child.number - 1])
        
        # add the child node in a list, it would be pickled later
        self.pickle_dataframe_list.append(child)

        if not child.isMail:
            # append the name of the node to be shown as the node label
            self.nodeText.append(directory)
        return child, self.max_depth


class H2Tree:
    pickle_dataset = None

    def __init__(self, ht_position_dict, ht_pickle_dataframe_list, 
                 ht_adjacency_list, ht_nodetext, ht_rs, ht_phi_0s,
                 ht_max_depth):
        """
        Initialize class level variables

        Keyword arguments:
        ht_position_dict: a dictionary holding the positions of all nodes
        ht_pickle_dataframe_list: a list containing all the nodes in the tree 
                                  graph
        ht_adjacency_list: a list containing the adjacent connections in the 
                           graph
        ht_nodetext: a list containing the label of all nodes
        ht_phi_0s: list containing the angle measure at various levels of the 
                   graph
        ht_max_depth: maximum depth of the tree graph
        """
        
        # creating an instance of the PyQt GraphicsWindow
        self.w = pg.GraphicsWindow()
        
        # set the title of the graphic window
        self.w.setWindowTitle("H2 Tree Representation of Emails")
        
        self.v = self.w.addViewBox()  # add a view box to the graphic window
        self.v.setAspectLocked()
        self.g = Graph()  # create an instance of the class Graph
        self.v.addItem(self.g)  # add the instance of the graph to the view box
        self.position_dict = ht_position_dict
        self.pickle_dataframe_list = ht_pickle_dataframe_list
        self.positions = []
        self.adjacency_list = ht_adjacency_list
        self.nodeText = ht_nodetext
        self.rs = ht_rs
        self.phi_0s = ht_phi_0s

        # list to maintain width of connections between nodes based on the node
        # sizes
        self.lines = []
        self.node_size = []  # list to maintain node sizes based on their sizes
        self.max_depth = ht_max_depth
        
        # flag to check whether the graph has been clicked or not
        self.reposition = False

    def operation_on_h2_tree(self, new_center_node=None, 
                             current_node_positions=None):
        """
        This method calls the hyperbolize method to hyperbolize the tree graph.
        Moreover, this method also calls other methods which effect the visuals
        of the graph

        Keyword arguments:
        new_center_node: if the graph has been clicked, then it would be the 
                         clicked node, else it would be root node
        current_node_positions: a dictionary holding the current positions of 
                                the nodes
        """

        self.hyperbolize(new_center_node)

        if current_node_positions:
            self.reposition = True
            self.position_dict = self.focus_node(current_node_positions, 
                                                 new_center_node)
        else:
            self.position_dict = self.focus_node(self.position_dict, 
                                                 new_center_node)
            
        # list to hold the positions of various nodes from the dictionary
        self.positions = []

        _pickle_dataset = PickleDataset()
        H2Tree.pickle_dataset = _pickle_dataset.get_pickle_dataset()
        
        for key in self.position_dict.keys():
            self.positions.append(self.position_dict[key])
            H2Tree.pickle_dataset[key - 1].position = self.position_dict[key]

        if not self.reposition:
            self.getsizeofdirectory()  # get the size of every directory
            
            # modify the width of lines connecting two nodes
            self.modify_edge_width()
            
            # modify the node sizes based on mail size
            self.modify_node_sizes()
            
        # method to render the H2 tree graph
        self.render_h2_tree(self.positions)

    def hyperbolize(self, node):
        """
        Method to hyperbolize the nodes of the tree recursively

        Keyword arguments:
        node: a node in the graph
        """

        # focus the graph either on the root node or the clicked node
        self.position_dict = self.focus_node(self.position_dict, node)

        if not self.reposition:
            # get the position of the children of the current node
            pos_children = \
                self.rs[node.depth] * np.exp(1j * linspace(
                    -self.phi_0s[node.depth],
                    self.phi_0s[node.depth],
                    len(node.children)
                ))

        # store the position of every node into the dictionary, with the node
        # number as the key for the dictionary
        for i, child in enumerate(node.children):
            if self.reposition:
                self.position_dict[child.number] = \
                (self.position_dict[child.number][0] * self.rs[node.depth],
                 self.position_dict[child.number][1] * self.rs[node.depth])
            else:
                self.position_dict[child.number] = \
                    (pos_children[i].real, pos_children[i].imag)

        # further hyperbolize every node in the tree graph
        for i, child in enumerate(node.children):
            self.hyperbolize(child)

    def focus_node(self, fn_position_dict, node):
        """
        The method returns the node, usually the root node, or the node which 
        has been clicked

        Keyword arguments:
        fn_position_dict: a dictionary containing the positions of all nodes
        node: nodes in the graph
        """

        c = complex(*fn_position_dict[node.number])
        if node.parent:
            pos_parent = \
                self.moebius(complex(*fn_position_dict[node.parent.number]), c)
            if not self.reposition:
                phi = -np.arctan2(-pos_parent.imag, - pos_parent.real)
            else:
                phi = 0
        else:
            phi = 0

        return self.focus_point(fn_position_dict, c, phi)

    @staticmethod
    def moebius(z, c=0, phi=0):
        """
        Möbius transformation
        """
        return exp(1j * phi) * (z - c) / (1 - conjugate(c) * z)

    def focus_point(self, fp_position_dict, c, phi=0):
        """
        Method to return the new position of the clicked node
        """
        pos = self.moebius(array([complex(*p) for p in 
                                  fp_position_dict.values()]), c, phi)
        return {node: (pos[i].real, pos[i].imag) for i, node in 
                enumerate(fp_position_dict)}

    def getsizeofdirectory(self):
        """
        Function to get the mail size under a directory and the number of mails
        within a directory.
        """

        try:
            # Start searching the sizes from the depth of the tree
            depth = self.max_depth

            # For every node (mail or directory) at a particular level,
            # update the size of the parent node a level above, as the sum of the
            # size of the node at the current depth
            while depth > 0:
                for node in self.pickle_dataset:
                    if node.depth == depth:
                        # increment the Email size under the parent node
                        node.parent.mailSize = node.parent.mailSize + node.mailSize
                        node.mailSize = node.mailSize

                        # increment the number of mails under parent node
                        if node.isMail:
                            node.parent.numberOfMails = \
                                node.parent.numberOfMails + 1

                        self.pickle_dataframe_list[node.number - 1] = node
                        self.pickle_dataframe_list[node.parent.number - 1] = \
                            node.parent

                # Once a level has been completely processed, move a level up
                depth = depth - 1
        except Exception as ex:
            print("An error happened in getsizeofdirectory method.\n")
            print(ex)

    def modify_edge_width(self):
        """
        Based on the size of child node, the width and color of lines in the 
        graph would be changed.
        """

        edges = []
        children = []

        for depth in range(0, self.max_depth):
            for node in self.pickle_dataset:
                if node.depth == depth:
                    children = node.children

                for child in children:
                    if 0 < child.mailSize < 20:
                        edges.append((173, 145, 140, 255, 1))
                    elif 20 <= child.mailSize < 50:
                        edges.append((186, 174, 117, 255, 1.5))
                    elif 50 <= child.mailSize < 100:
                        edges.append((54, 89, 68, 255, 2))
                    elif 100 <= child.mailSize < 500:
                        edges.append((199, 214, 221, 255, 2.5))
                    elif 500 <= child.mailSize < 1000:
                        edges.append((144, 106, 221, 255, 3))
                    elif child.mailSize >= 1000:
                        edges.append((219, 85, 141, 255, 3.5))

        self.lines = np.array(edges, dtype=[("red", np.ubyte),
                                            ("green", np.ubyte),
                                            ("blue", np.ubyte),
                                            ("alpha", np.ubyte),
                                            ("width", float)])

    def modify_node_sizes(self):
        """
        Method to modify the node sizes based on the mail_size of the node
        """

        # The sizes of the node compared are in kilobytes
        for node in H2Tree.pickle_dataset:
            if 0 <= node.mailSize < 10:
                self.node_size.append(0.02)
            elif 10 <= node.mailSize < 100:
                self.node_size.append(0.04)
            elif 100 <= node.mailSize < 500:
                self.node_size.append(0.06)
            elif 500 <= node.mailSize < 1000:
                self.node_size.append(0.08)
            elif 1000 <= node.mailSize < 10000:
                self.node_size.append(0.09)
            else:
                self.node_size.append(0.11)

    def render_h2_tree(self, positions):
        """
        Method to render the H2 tree map embedded in Poincare disc

        Keyword arguments:
        positions: 2D positions of nodes in the tree graph
        """

        # set the nodes in the graphic window
        self.adjacency_list = np.array(self.adjacency_list)
        positions = np.array(positions)
        self.g.setData(pos=positions, adj=self.adjacency_list, 
                       size=self.node_size, pxMode=False,
                       text=self.nodeText, pen=self.lines)

        # g2 and g3 are graph items representing two semicircles.
        # These two semicircles will then be joined to form one whole Poincare
        # disc
        g2 = pg.GraphItem()
        self.v.addItem(g2)
        g3 = pg.GraphItem()
        self.v.addItem(g3)

        self.plot_poincare_disc(g2, g3)

    @staticmethod
    def plot_poincare_disc(graph_item_1, graph_item_2):
        """
        Construct a unit radius circle in which the tree graph would be 
        rendered.

        Keyword arguments:
        graph_item_1: semi-circle 1
        graph_item_2: semi-circle 2
        """

        # Two semicircles have been produced first and then joined later
        # As PyQtGraph needs a position matrix along with an adjacency matrix,
        # hence pos and adj arrays

        # Semi-Circle 1
        pos1 = []
        adj1 = []
        length = 0

        # calculating y coordinates for 1000 evenly spaced points in (-1,1)
        for x in np.linspace(-1, 1, 1000):
            y = math.sqrt(1 - x ** 2)
            pos1.append([x, y])
            if len(pos1) > 1:
                adj1.append([length - 1, length])
            length = length + 1

        pos1 = np.array(pos1)
        adj1 = np.array(adj1)
        graph_item_1.setData(pos=pos1, adj=adj1, size=0.07)

        # Semi-circle 2
        pos2 = []
        adj2 = []
        length = 0

        # calculating y coordinates for 1000 evenly spaced points in (1,-1)
        for x in np.linspace(1, -1, 1000):
            y = -math.sqrt(1 - x ** 2)
            pos2.append([x, y])
            if len(pos2) > 1:
                adj2.append([length - 1, length])
            length = length + 1

        pos2 = np.array(pos2)
        adj2 = np.array(adj2)
        graph_item_2.setData(pos=pos2, adj=adj2, size=0.07)


if __name__ == "__main__":
    ######################
    # Variable declaration
    ######################
    
    # stores the adjacency links between two nodes in the graph
    adjacency_list = []
    
    nodeText = []  # stores the labels assigned to the nodes in the graph
    
    # to store the node objects in the form of a list
    pickle_dataframe_list = []
    
    # to store the sizes of nodes in the graph based on the mail sizes
    node_size = []
    
    node_colors = []  # list to store the brush color of nodes in the graph
    index = 1  # starting index of the panda dataset

    ######################################
    # Configuring the PyQt graphics window
    ######################################
    
    # set the background color of the PyQt window
    pg.setConfigOption("background", 0.35)
    
    # set the foreground color of the PyQt window
    pg.setConfigOption("foreground", 'y')
    pg.setConfigOptions(antialias=True)

    # Corresponding to the month's name in the mail timestamp, name would be
    # replaced by month number.
    month_dict = {"Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
                  "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
                  "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"}

    # Root node would be the default center node in the H2 tree graph.
    # The graph would originate from root node only.
    
    # Create a root node for the tree. Call the node by the name 'Root'.
    root = Node(name="Root")

    # By default the root node would be at position (0,0) of 2D coordinate
    # system. The nodes are stored in the form of a dictionary with key as the
    # node number and the position as value.
    position_dict = {root.number: (0, 0)}
    nodeText.append("Root")
    pickle_dataframe_list.append(root)

    # Log in the server to fetch details
    login = Login(imap_server_name, user)

    # Store the IMAP server object, as it would be required for further IMAP
    # server operations.
    svr = login.svr_obj

    # create an object of the class IMAPParse
    imap_parse = ImapParse(svr, root, index, columns, dataset_path, nodeText, 
                           month_dict, pickle_dataframe_list)

    pickle_dataset = PickleDataset()

    # Check if the panda dataset exists at the dataset path.
    # If it exists, then synchronize the IMAP server current state with the data
    # in the panda dataset, else start downloading all the details from the IMAP
    # server.
    if not os.path.isfile(dataset_path):
        try:
            imap_parse.parse_server(False)
        
        except Exception as ex:
            print(ex)
            
            if os.path.isfile(dataset_path) and \
                    not os.path.isfile(pickle_dataset_path):
                os.remove(dataset_path)
                                
                print("While TreeDataFrame.pkl file was not created, removing "
                      "the file DataFrame.csv, as it would cause issues with "
                      "subsequent runs.\n")
                
                print("The program terminated abnormally. Please fix any "
                      "issues and then re-run the script.")
            sys.exit()

        imap_tree = ImapTree(nodeText, pickle_dataframe_list, adjacency_list)
        
        # adjacency matrix for the IMAP server
        adjacency_list = np.array(imap_tree.adjacency_list)

        nodeText = imap_tree.nodeText
        pickle_dataframe_list = imap_tree.pickle_dataframe_list
    
    else:
        original_dataframe = dataset_path
        # copied_dataframe = r"D:\Bielefeld\Individual Project\DataFrame_copy.csv"
        copied_dataframe = data_path + "/" + dataset_path.split('.')[0] + "_copy.csv"   # TH bug fix
        copyfile(original_dataframe, copied_dataframe)
        
        original_pickle = pickle_dataset_path
        # copied_pickle = \
        #     r"D:\Bielefeld\Individual Project\TreeDataFrame_copy.pkl"
        copied_pickle = data_path + "/" + original_pickle.split('.')[0] + "_copy.pkl"   #  TH bug fix
        copyfile(original_pickle, copied_pickle)

        # In certain cases, when the script connects to the IMAP server and
        # tries to synchronize an error occurs. This error could be due to
        # issues in the script, a wrong action trying to be executed on the
        # server, etc. Due to any such issue, the script may/may not update
        # partial details in the DataFrame.csv file and exit. This causes
        # synchronization issues with the TreeDataFrame.pkl file.
        # In such cases, the script replaces the newly updated DataFrame.csv
        # file with the last correct version of itself. Similarly, to ensure
        # that TreeDataFrame.pkl is also consistent, it is also replaced by the
        # last correct version of itself.
        try:
            imap_parse.parse_server(True)
            
        except Exception as ex:
            print(ex)            
            
            os.remove(original_dataframe)
            os.remove(original_pickle)
            
            os.rename(copied_dataframe, dataset_path)
            os.rename(copied_pickle, pickle_dataset_path)
            
            print("\nAn error occurred during synchronization call to the IMAP "
                  "server. The last version of the dataframe have been "
                  "successfully restored.\n")
            print("Please fix the issues occurring and re-run the script.\n")
            print("Exiting....")
            
            sys.exit()

        os.remove(copied_dataframe)
        os.remove(copied_pickle)

        # All the nodes have been read from the pickle dataset and stored in
        # the form of a dictionary
        
        # retrieve the Root node from the pickle dataset
        root = imap_parse.node_dict["Root"]

        # list of the labels of various nodes retrieved from pickle dataset
        # after syncing with mail server
        nodeText = imap_parse.nodeText

        # list of all the node objects stored in the pickle dataset
        pickle_dataframe_list = imap_parse.pickle_dataframe_list

        # once the local dataset has been synced with the IMAP server, dump
        # the dataset to the same path again
        pickle_dataset.dump_pickle_dataset(pickle_dataframe_list)

    rs = ones(max(0, 7)) * .5
    phi_0s = ones(max(0, 7)) * 2 * pi / 9.0
    phi_0s[0:7] = [2 * pi / 3, 1 * pi / 3, .9 * pi / 3, pi / 5, pi / 3, pi / 3,
                   pi / 3]
    rs[0:7] = [.3, .5, .4, .5, .3, .3, .3]

    # Create an instance of the H2tree class. This object would be used to
    # render the H2 tree graph
    h2_tree = H2Tree(position_dict, pickle_dataframe_list, adjacency_list, 
                     nodeText, rs, phi_0s, imap_parse.max_depth)

    # Check if all the node information is already present on the local
    # file system. If there is no .pkl file dump the content to .pkl file.
    # Based on the content of .pkl file the size of the nodes and the link
    # widths would be modified.
    if not os.path.exists(pickle_dataset_path):
        pickle_dataset.dump_pickle_dataset(pickle_dataframe_list)

    h2_tree.operation_on_h2_tree(root)

    app = QApplication(sys.argv)
    
    widget = Widget(imap_parse.latestYear, imap_parse.oldestYear, 
                    adjacency_list, nodeText, h2_tree.g,
                    h2_tree.node_size, h2_tree.lines, h2_tree.w)
    widget.show()
    sys.exit(app.exec_())
