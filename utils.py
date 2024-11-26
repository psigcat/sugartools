# -*- coding: utf-8 -*-

__author__ = '(C) 2023 by Gerald Kogler'
__date__ = '26/11/2024'
__copyright__ = 'Copyright 2024, PSIG'
__license__ = 'GPLv3 license'


class Utils:
    """Sugar utilities."""

    def sec_set_uas(par_levels):
        """ Set UA's query """

        levels_str = par_levels

        try:
            levels_lst = levels_str.split(',')
            levels_query = "nom_nivel = '" + levels_lst[0] + "'"
            for i in levels_lst:
                if i != levels_lst[0]:
                    levels_query += " OR nom_nivel = '" + i + "'"
        except:
            print("Error getting levels. Check the format.")
            print(str(levels_str))

        return levels_str, levels_query