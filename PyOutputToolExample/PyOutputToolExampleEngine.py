import AlteryxPythonSDK
import xml.etree.ElementTree as ET
import os
import csv

class AyxPlugin:
    """
    Implements the plugin interface methods, to be utilized by the Alteryx engine to communicate with a plugin.
    Prefixed with "pi_", the Alteryx engine will expect the below five interface methods to be defined.
    """
    def __init__(self, n_tool_id: int, alteryx_engine: object, output_anchor_mgr: object):
        """
        Acts as the constructor for AyxPlugin.
        :param n_tool_id: The assigned unique identification for a tool instance.
        :param alteryx_engine: Provides an interface into the Alteryx engine.
        :param generic_engine: An abstraction of alteryx_engine.
        :param output_anchor_mgr: A helper that wraps the outgoing connections for a plugin.
        """

        # Miscellaneous variables
        self.n_tool_id = n_tool_id
        self.name = 'PyOutputToolExample_' + str(self.n_tool_id)
        self.initialized = False

        # Engine handles
        self.alteryx_engine = alteryx_engine

        # Custom members
        self.str_file_path = None

    def pi_init(self, str_xml: str):
        """
        Called when the Alteryx engine is ready to provide the tool configuration from the GUI.
        :param str_xml: The raw XML from the GUI.
        """

        # Extracting configuration xml
        root = ET.fromstring(str_xml)

        try: # Finding the dataName property from the Gui.html that matches the child node
            self.str_file_path = root.find('fileOutputPath').text
        except AttributeError:
            self.alteryx_engine.output_message(self.n_tool_id, AlteryxPythonSDK.EngineMessageType.error, self.xmsg('Invalid XML: ' + str_xml))
            raise

    def pi_add_incoming_connection(self, str_type: str, str_name: str) -> object:
        """
        The IncomingInterface objects are instantiated here, one object per incoming connection.
        Called when the Alteryx engine is attempting to add an incoming data connection.
        :param str_type: The name of the input connection anchor, defined in the Config.xml file.
        :param str_name: The name of the wire, defined by the workflow author.
        :return: The IncomingInterface object(s).
        """
        self.single_input = IncomingInterface(self)
        return self.single_input

    def pi_add_outgoing_connection(self, str_name: str):
       """
       Called when the Alteryx engine is attempting to add an outgoing data connection.
       :param str_name: The name of the output connection anchor, defined in the Config.xml file.
       :return: True signifies that the connection is accepted.
       """
       return True

    def pi_push_all_records(self, n_record_limit: int) -> bool:
        """
        Called by the Alteryx engine for tools that have no incoming connection connected.
        Only pertinent to tools which have no upstream connections, like the Input tool.
        :param n_record_limit: Set it to <0 for no limit, 0 for no records, and >0 to specify the number of records.
        :return: True for success, False for failure.
        """
        self.alteryx_engine.output_message(self.n_tool_id, AlteryxPythonSDK.EngineMessageType.error, self.xmsg('Missing Incoming Connection'))
        return False

    def pi_close(self, b_has_errors: bool):
        """
        Called after all records have been processed..
        :param b_has_errors: Set to true to not do the final processing.
        """
        pass

    def xmsg(self, msg_string: str) -> str:
        """
        A non-interface, non-operational placeholder for the eventual localization of predefined user-facing strings.
        :param msg_string: The user-facing string.
        :return: msg_string
        """

        return msg_string

    @staticmethod
    def write_lists_to_csv(file_temp_path: str, field_lists: list):
        """
        A non-interface, helper function that handles writing to csv and clearing the list elements.
        :param file_temp_path: The default temp path and file name.
        :param field_lists: The data for all fields.
        """

        with open(file_temp_path, 'a', encoding='utf-8', newline='') as output_file:
            csv.writer(output_file, delimiter=',').writerows(zip(*field_lists))
        for sublist in field_lists:
            del sublist[:]

class IncomingInterface:
    """
    This class is returned by pi_add_incoming_connection, and it implements the incoming interface methods, to be
    utilized by the Alteryx engine to communicate with a plugin when processing an incoming connection.
    Prefixed with "ii_", the Alteryx engine will expect the below four interface methods to be defined.
    """

    def __init__(self, parent: object):
        """
        Acts as the constructor for IncomingInterface. Instance variable initializations should happen here for PEP8 compliance.
        :param parent: AyxPlugin
        """

        # Miscellaneous properties
        self.parent = parent

        # Record management
        self.record_info_in = None

        # Custom members
        self.field_names = None
        self.field_lists = []
        self.counter = 0
        self.special_chars = set('/;?*"<>|')

    def ii_init(self, record_info_in: object) -> bool:
        """
        Called when the incoming connection's record metadata is available or has changed, and
        has let the Alteryx engine know what its output will look like.
        :param record_info_in: A RecordInfo object for the incoming connection's fields.
        :return: True for success, otherwise False.
        """

        # Storing the argument being passed to the record_info_in parameter
        self.record_info_in = record_info_in

        # Storing the field names
        for field in range(record_info_in.num_fields):
            self.field_lists.append([record_info_in[field].name])

        if self.parent.str_file_path is not None and os.access(self.parent.str_file_path, os.F_OK):
            # Outputting Error message if user specified file already exists
            self.parent.alteryx_engine.output_message(self.parent.n_tool_id, AlteryxPythonSDK.EngineMessageType.error, self.parent.xmsg('Error: ' + self.parent.str_file_path + ' already exists. Please enter a different path.'))

        # Check length of filename
        if self.parent.str_file_path is not None and len(self.parent.str_file_path) > 259:
            self.parent.alteryx_engine.output_message(self.parent.n_tool_id, AlteryxPythonSDK.EngineMessageType.error, self.parent.xmsg('Maximum path length is 259'))
        
        # Check for special characters in filename
        if self.parent.str_file_path is not None and any((c in self.special_chars) for c in self.parent.str_file_path):
            self.parent.alteryx_engine.output_message(self.parent.n_tool_id, AlteryxPythonSDK.EngineMessageType.error, self.parent.xmsg('These characters are not allowed in the filename: /;?*"<>|'))
        
        # Show error is filename is blank
        if self.parent.str_file_path is None or len(self.parent.str_file_path) == 0:
            self.parent.alteryx_engine.output_message(self.parent.n_tool_id, AlteryxPythonSDK.EngineMessageType.error, self.parent.xmsg('Enter a filename'))

        return True

    def ii_push_record(self, in_record: object) -> bool:
        """
         Called when an input record is being sent to the plugin.
         :param in_record: The data for the incoming record.
         :return: True for accepted record.
         """

        self.counter += 1

        # Storing the string data of in_record
        for field in range(self.record_info_in.num_fields):
            in_value = self.record_info_in[field].get_as_string(in_record)
            self.field_lists[field].append(in_value) if in_value is not None else self.field_lists[field].append('')

        # Writing when chunk mark is met
        if self.counter == 1000000:
            self.parent.write_lists_to_csv(self.parent.str_file_path, self.field_lists)
            self.counter = 0 # Reset counter

        return True

    def ii_update_progress(self, d_percent: float):
        """
         Called when by the upstream tool to report what percentage of records have been pushed.
         :param d_percent: Value between 0.0 and 1.0.
        """

        # Inform the Alteryx engine of the tool's progress.
        self.parent.alteryx_engine.output_tool_progress(self.parent.n_tool_id, d_percent)

    def ii_close(self):
        """
        Called when the incoming connection has finished passing all of its records.
        """

        # Write the last chunk
        if len(self.field_lists[0]) > 1: # First element for each list will always be the field names.
            self.parent.write_lists_to_csv(self.parent.str_file_path, self.field_lists)

        if self.parent.str_file_path is not None:
            # Outputting message that the file was written
            self.parent.alteryx_engine.output_message(self.parent.n_tool_id, AlteryxPythonSDK.Status.file_output, self.parent.xmsg(self.parent.str_file_path + "|" + self.parent.str_file_path + " was created."))
