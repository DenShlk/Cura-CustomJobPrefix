# Copyright (c) 2020 Aldo Hoeben / fieldOfView
# CustomJobPrefix is released under the terms of the AGPLv3 or higher.

import os.path

from UM.Extension import Extension
from UM.Logger import Logger
from cura.CuraApplication import CuraApplication

from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from . import PrintInformationPatches
from . import OutputDevicePatcher

from UM.i18n import i18nCatalog
catalog = i18nCatalog("cura")

from typing import Optional

class CustomJobPrefix(Extension, QObject,):
    def __init__(self, parent = None) -> None:
        QObject.__init__(self, parent)
        Extension.__init__(self)

        self._application = CuraApplication.getInstance()

        self.addMenuItem(catalog.i18nc("@item:inmenu", "Set name options"), self.showNameDialog)

        self._prefix_dialog = None  # type: Optional[QObject]
        self._print_information_patches = None  # type: Optional[PrintInformationPatches.PrintInformationPatches]
        self._output_device_patcher = OutputDevicePatcher.OutputDevicePatcher()

        self._application.engineCreatedSignal.connect(self._onEngineCreated)
        self._application.globalContainerStackChanged.connect(self._onGlobalStackChanged)

    def _onEngineCreated(self) -> None:
        self._print_information_patches = PrintInformationPatches.PrintInformationPatches(self._application.getPrintInformation())
        self._createAdditionalComponentsView()

    def _createAdditionalComponentsView(self) -> None:
        Logger.log("d", "Creating additional ui components for CustomJobPrefix")

        try:
            major_api_version = self._application.getAPIVersion().getMajor()
        except AttributeError:
            # UM.Application.getAPIVersion was added for API > 6 (Cura 4)
            # Since this plugin version is only compatible with Cura 3.5 and newer, it is safe to assume API 5
            major_api_version = 5

        if major_api_version <= 5:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml", "JobSpecsPatcher3x.qml")
        else:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml", "JobSpecsPatcher4x.qml")

        self._additional_components = self._application.createQmlComponent(path, {"customJobPrefix": self})
        if not self._additional_components:
            Logger.log("w", "Could not create additional components for CustomJobPrefix")
            return

        self._application.addAdditionalComponent("jobSpecsButton", self._additional_components)
        self._additional_components.patchParent()

    def _onGlobalStackChanged(self) -> None:
        self.jobAffixesChanged.emit()

    @pyqtSlot()
    def showNameDialog(self) -> None:
        global_container_stack = self._application.getGlobalContainerStack()
        if not global_container_stack:
            return

        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml", "PrefixDialog.qml")
        self._prefix_dialog = self._application.createQmlComponent(path, {"manager": self})
        if self._prefix_dialog:
            self._prefix_dialog.show()

    jobAffixesChanged = pyqtSignal()

    @pyqtSlot(str, str, str)
    def setJobAffixes(self, prefix: str, postfix: str, path: str) -> None:
        global_container_stack = self._application.getGlobalContainerStack()
        if not global_container_stack:
            return

        global_container_stack.setMetaDataEntry("custom_job_prefix", prefix)
        global_container_stack.setMetaDataEntry("custom_job_postfix", postfix)
        global_container_stack.setMetaDataEntry("custom_job_path", path)
        self.jobAffixesChanged.emit()

    @pyqtProperty(str, notify=jobAffixesChanged)
    def jobPrefix(self) -> str:
        global_container_stack = self._application.getGlobalContainerStack()
        if not global_container_stack:
            return ""

        return global_container_stack.getMetaDataEntry("custom_job_prefix", "{printer_type}")

    @pyqtProperty(str, notify=jobAffixesChanged)
    def jobPostfix(self) -> str:
        global_container_stack = self._application.getGlobalContainerStack()
        if not global_container_stack:
            return ""

        return global_container_stack.getMetaDataEntry("custom_job_postfix", "")

    @pyqtProperty(str, notify=jobAffixesChanged)
    def jobPath(self) -> str:
        global_container_stack = self._application.getGlobalContainerStack()
        if not global_container_stack:
            return ""

        return global_container_stack.getMetaDataEntry("custom_job_path", "")

    @pyqtProperty(QObject, constant=True)
    def printInformation(self) -> Optional[PrintInformationPatches.PrintInformationPatches]:
        return self._print_information_patches
