# -*- coding: utf-8 -*-
"""
/***************************************************************************
 VogisSuche
                                 A QGIS plugin
 Lucene-Suche für das VoGIS
                             -------------------
        begin                : 2016-04-27
        copyright            : (C) 2016 by Peter Drexel
        email                : peter.drexel@vorarlberg.at
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load VogisSuche class from file VogisSuche.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .vogis_suche import VogisSuche
    return VogisSuche(iface)
