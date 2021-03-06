"""
CDAS FileStore Module

Cybersecurity Decision Analysis Simulator (CDAS)

Copyright 2020 Carnegie Mellon University.

NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE
MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO
WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER
INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR
MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL.
CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT
TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.

Released under a MIT (SEI)-style license, please see license.txt or contact
permission@sei.cmu.edu for full terms.

[DISTRIBUTION STATEMENT A] This material has been approved for public release
and unlimited distribution.  Please see Copyright notice for non-US Government
use and distribution.

Carnegie Mellon® and CERT® are registered in the U.S. Patent and Trademark
Office by Carnegie Mellon University.

This Software includes and/or makes use of the following Third-Party Software
subject to its own license:
1. numpy (https://numpy.org/doc/stable/license.html)
    Copyright 2005 Numpy Developers.
2. reportlab (https://bitbucket.org/rptlab/reportlab/src/default/LICENSE.txt)
    Copyright 2000-2018 ReportLab Inc.
3. drawSvg (https://github.com/cduck/drawSvg/blob/master/LICENSE.txt)
    Copyright 2017 Casey Duckering.
4. Cyber Threat Intelligence Repository (Mitre/CTI)
    (https://github.com/mitre/cti/blob/master/LICENSE.txt)
    Copyright 2017 Mitre Corporation.

DM20-0573
"""

from datetime import datetime
import json
import os
import re
import reportlab.platypus as platy
from reportlab.lib.styles import getSampleStyleSheet
import shutil
import sys
from . import context


class FileStore():
    """
    For saving, loading, and searching files of specific object types.

    Args:
        path (str): directory path where the files (will) exist
        data_type (Object name): what type of data (will) exist in
            the directory
        write (bool, optional): whether the directory is writable. Defaults to
            False.

    Attributes:
        _type (Object): stores data_type arg
        _write (bool): stores write arg
        path (str): stores path arg

    Raises:
        FileNotFoundError: if path does not already exist and _write is set to
            False
    """

    def __init__(self, path, data_type, write=False):

        self._type = data_type
        self._write = write

        if not os.path.isdir(path):
            if self._write is False:
                raise FileNotFoundError(f'{path} is not a directory.')
            os.mkdir(path)
        # Check if there are already files in the given directory and test
        # whether they have the correct format
        if os.path.isdir(path) and write is False:
            for f in os.listdir(path):
                if not f.endswith(self._type._file_specification['ext']):
                    raise Exception(
                        f"file {f} in {path} is not allowed for "
                        f"{self._type.__name__}. Extension must be ."
                        f"{self._type._file_specification['ext']}.")
                if not f.startswith(self._type._file_specification['prefix']):
                    raise Exception(
                        f"file {f} in {path} is not allowed for "
                        f"{self._type.__name__}. Must start with \""
                        f"{self._type._file_specification['prefix']}\".")
                with open(os.path.join(path, f)) as j_file:
                    obj = json.load(j_file)
                j_file.close()
                missing_attrs = [
                    attr for attr in self._type._file_specification['req_attrs']
                    if attr not in obj.keys()]
                if len(missing_attrs) > 0:
                    raise Exception(
                        f'{self._type.__name__} {os.path.join(path, f)} is '
                        f'missing the required attributes: '
                        f'{", ".join(missing_attrs)}.')
                if obj['id'] != f[:-5]:
                    raise Exception(
                        f'id, "{obj["id"]}", for {self._type.__name__}, {f}, '
                        f'does not match filename. id should be "{f[:-5]}".')

        # Check if there are already files in the given directory and if it's
        # okay to overwrite them
        if os.path.isdir(path) and write is True and len(os.listdir(path)) > 0:
            q = (f'Overwrite the {self._type} folder {path}? (y/n) ')
            answer = ""
            while answer not in ['y', 'n']:
                answer = input(q)
            if answer == 'n':
                sys.exit()
            else:
                for filename in os.listdir(path):
                    fp = os.path.join(path, filename)
                    try:
                        if os.path.isfile(fp) or os.path.islink(fp):
                            os.unlink(fp)
                        elif os.path.isdir(fp):
                            shutil.rmtree(fp)
                    except Exception as e:
                        print(f'Failed to delete {fp}. {e}')
        self.path = path

    def get(self, ids):
        """
        Instantiates an object from a .json file

        Args:
            ids (str): filename (with or without .json extension)

        Returns:
            found_object: instance of the requested item
        """

        if not isinstance(ids, str):
            raise Exception(f'ids should be string not {type(ids)}')

        # read in each file and instantiate the object from the json
        filename = os.path.join(self.path, ids)
        if not filename.endswith('.json'):
            filename += '.json'
        with open(filename) as j_file:
            obj = json.load(j_file)
        j_file.close()

        return self._type(**obj)

    def list_files(self):
        """Return all filenames in the FileStore"""

        filenames = []
        for f in os.listdir(self.path):
            filenames.append(f)
        return filenames

    def output(self, subfolder, obj_to_output, filetype):
        """
        Saves objects to files of the given filetype

        Internally, CDAS uses json formatted files, object instances, and
        dictionaries. This function saves the objects to whatever filetype the
        user has specified for final output.

        Args:
            subfolder (str): name of the subfolder within the FileStore, within
                which to save the output
            obj_to_output (instance of an object): thing to write to the file
            filetype (str): one of the available types for file output (pdf,
                json, html)
        """

        if filetype not in ['json', 'html', 'pdf', 'misp']:
            raise ValueError(f'{filetype} is not an accepted filetype.')

        if filetype == 'json':
            filepath = os.path.join(
                self.path, subfolder,
                obj_to_output.id + '.' + filetype)
            with open(filepath, 'w') as outfile:
                json.dump(obj_to_output._serialize(), outfile, indent=4)
            outfile.close()
        elif filetype == 'html':
            filepath = os.path.join(
                self.path, subfolder,
                obj_to_output.name + '.json')
            f = open(filepath, 'w')
            f.write("var data = " + str(obj_to_output._serialize()))
            f.close()
        elif filetype == 'pdf':
            filepath = os.path.join(
                self.path, subfolder,
                obj_to_output.name.replace(' ', '') + '.' + filetype)
            ss = getSampleStyleSheet()
            pdf = platy.SimpleDocTemplate(filepath)
            flowables = [platy.Paragraph(obj_to_output.name, ss['Heading1'])]
            for header, details in obj_to_output._pdf_headers.items():
                flowables.append(platy.Paragraph(header, ss['Heading2']))
                for detail in details:
                    try:
                        d_value = vars(obj_to_output)[detail]
                    except KeyError:
                        continue
                    if len(details[detail]) > 0:
                        p = details[detail] + ': '
                    else:
                        p = ''
                    if type(d_value) is str or type(d_value) is int:
                        p += str(d_value)
                        flowables.append(platy.Paragraph(p, ss['BodyText']))
                    elif isinstance(d_value, datetime):
                        p += datetime.strftime(d_value, "%d %b %Y %H:%M")
                        flowables.append(platy.Paragraph(p, ss['BodyText']))
                    else:
                        flowables.append(platy.Paragraph(p, ss['BodyText']))
                        bullets = []
                        for v in d_value:
                            if type(v) is dict:
                                p = str(v)
                            else:
                                p = v
                            if type(d_value) is not list:
                                p += ": "+d_value[v]
                            b = platy.Paragraph(p, ss['Normal'])
                            bullets.append(platy.ListItem(b, leftIndent=35))
                        table = platy.ListFlowable(bullets, bulletType='bullet')
                        flowables.append(table)
            pdf.build(flowables)
        elif filetype == 'misp':
            pass
        else:
            raise ValueError(
                f'{filetype} is not a valid filetype. Check your config file.')

    def query(self, query_string, headers=False):
        """
        Search through the FileStore for matching files.

        Basic (i.e. not super-great) search functionality to look through all
        files in the FileStore for files that match given contraints. Returns
        the requested attributes of any matching files.

        Args:
            query_string (str): SQL-like query string of the format
                "SELECT attr1,attr2,etc WHERE 'attr3=test'"
            headers (bool, optional): whether include the list of
                requested attributes. Defaults to False.

        Returns:
            list of tuples consisting of requested attributes of matching files
        """

        # split the query string into the key components
        if not query_string.upper().startswith("SELECT "):
            raise Exception(
                f'query_string must start with "SELECT ". {query_string}')
        if " WHERE " in query_string.upper():
            get_attrs = query_string[7:query_string.find(" WHERE ")].split(',')
            q_where = query_string[query_string.find(" WHERE ")+7:]
            q_where = q_where.replace('AND', 'and').replace('OR', 'or')
            q_where = q_where.replace('=', '==').replace('<>', '!=')
            q_where = q_where.replace(';', '')
        else:
            get_attrs = query_string[7:].split(',')
            q_where = None

        # find all of the attribute names in the WHERE clause
        if q_where:
            clauses = re.split('and | or', q_where)
            where_attrs = []
            for c in clauses:
                if '==' in c:
                    operator = '=='
                elif '!=' in c:
                    operator = '!='
                elif '<' in c:
                    operator = '<'
                elif '>' in c:
                    operator = '>'
                elif '<=' in c:
                    operator = '<='
                elif '>=' in c:
                    operator = '>='
                else:
                    raise ValueError(f'Unrecognized operator in "{c}"')
                clause = re.split(operator, c)
                attr = clause[0].strip().lstrip('(')
                where_attrs.append((attr, operator))

        # Load each file in the data store
        selected = []
        for f in os.listdir(self.path):
            with open(os.path.join(self.path, f)) as json_file:
                obj_dict = json.load(json_file)
                json_file.close()

            # check for filtering criteria
            where_check = q_where
            if q_where is not None:
                for attr in where_attrs:
                    # change out the attribute name in the WHERE clause
                    #   for their values from the current object
                    try:
                        obj_val = obj_dict[attr[0]]
                        where_check = where_check.replace(
                            ''.join(attr), "'"+obj_val+"'"+attr[1])
                    except KeyError:
                        where_check = where_check.replace(
                            ''.join(attr), "'"+attr[0]+"'"+attr[1])

                matches = eval(where_check)
                if not matches:
                    continue

            match = ()
            for attr in get_attrs:
                try:
                    match += (obj_dict[attr],)
                except KeyError:
                    match += (None,)
            selected.append(match)

        if headers:
            return get_attrs, selected
        else:
            return selected

    def save(self, objects, overwrite=False):
        """
        Save serialized object instances to the filestore as json files.

        Args:
            objects (object instance or list of object instances): thing to
                save as a json file
            overwrite (bool, optional): Whether to overwrite existing files
                with the same file name as the current object. Defaults to
                False.

        Raises:
            Exception: if the file already exists and the FileStore is not
                writeable
        """

        if not isinstance(objects, list):
            objects = [objects]
        for obj in objects:
            filepath = os.path.join(self.path, obj.id)

            if os.path.isfile(filepath + '.json') and not overwrite:
                raise Exception(
                    f'Object {obj.id} already exists in '
                    f'{self.path}. Add "overwrite=True" to overwrite.')

            serialized = obj._serialize()
            with open(filepath + '.json', 'w') as outfile:
                json.dump(serialized, outfile, indent=4)
            outfile.close()

    def save_misp(self, path, filestore):
        """
        Save object instances to MISP files by leveraging each object's 
        mispizer function and dumping to a json file.

        Args:
            path (string): file to save the MISP output
            filestore (FileStore object): location of the object instances to
                save as MISP output
        """

        items = [filestore.get(i[0]) for i in filestore.query("SELECT id")]
        mispized = []
        for item in items:
            # Get the item in the format needed for MISP
            mispized.append(item._mispizer())
        if isinstance(items[0], context.Event):
            data = {'response': mispized}
        else:
            data = mispized
        with open(path, 'w') as outfile:
            json.dump(data, outfile, indent=4)
        outfile.close()
