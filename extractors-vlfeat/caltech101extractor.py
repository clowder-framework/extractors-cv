#!/usr/bin/env python

import subprocess
import os
import logging
import sys
from pyclowder.extractors import Extractor
import pyclowder.files


class Caltech101(Extractor):
    # Object classification extractor based on Caltech101 dataset
    def __init__(self):
        Extractor.__init__(self)

        # add any additional arguments to parser
        # self.parser.add_argument('--max', '-m', type=int, nargs='?', default=-1,
        #                          help='maximum number (default=-1)')
        # Path to MATLAB program
        self.parser.add_argument('--matlab-binary', '-mat', dest="matlab_binary", type=str, nargs='?',
                                 default=os.getenv("MATLAB_BINARY", "matlab"),
                                 help='Path to MATLAB binary file (default="matlab")')

        # parse command line and load default logging configuration
        self.setup()

        # setup logging for the extractor
        logging.getLogger('pyclowder').setLevel(logging.DEBUG)
        logging.getLogger('__main__').setLevel(logging.DEBUG)

        # assign other arguments
        self.matlab_process = None
        self.matlab_binary = self.args.matlab_binary

    def process_message(self, connector, host, secret_key, resource, parameters):

        file_id = resource['id']
        input_file = resource['local_paths'][0]
        tmpfile = input_file + ".txt"

        try:
            self.run_classify(input_file, tmpfile)

            # tmpfile resulting from running the matlab code should contain two lines. 1st = category, 2nd = score
            f = open(tmpfile, 'r')
            category = f.readline().strip('\n')
            score = f.readline().strip('\n')
            f.close()

            # store results as metadata
            result = {
                "basic_caltech101_category": category,
                "basic_caltech101_score": score
            }
            metadata = self.get_metadata(result, 'file', file_id, host)
            pyclowder.files.upload_metadata(connector, host, secret_key, file_id, metadata)

        finally:
            if os.path.isfile(tmpfile):
                os.remove(tmpfile)

    def run_classify(self, inputfile, outputfile):

        if not self.matlab_process or self.matlab_process.poll():
            folder = os.path.dirname(os.path.realpath(__file__))
            args = [self.matlab_binary, '-nodisplay', '-nosplash', '-nodesktop', '-noFigureWindows']
            self.matlab_process = subprocess.Popen(args, stdin=subprocess.PIPE, shell=True, stdout=subprocess.PIPE)
            self.matlab_process.stdin.write("cd '" + folder + "';\n")
            self.matlab_process.stdin.write("run('./vlfeat/toolbox/vl_setup');\n")
            self.matlab_process.stdin.write("cd('./vlfeat/apps/');\n")
            self.matlab_process.stdin.write("load('./data/baseline-model.mat');\n")
            self.matlab_process.stdin.write("cd '" + folder + "';\n")

        self.matlab_process.stdin.write("image = imread('" + inputfile + "');\n")
        self.matlab_process.stdin.write("[label, score] = model.classify(model, image);\n")
        self.matlab_process.stdin.write("fileID = fopen('" + outputfile + "','w');\n")
        self.matlab_process.stdin.write("fprintf(fileID,'%s\\n', label);\n")
        self.matlab_process.stdin.write("fprintf(fileID,'%f\\n', score);\n")
        self.matlab_process.stdin.write("fclose(fileID);\n")
        self.matlab_process.stdin.write("disp('CALTECH101_DONE');\n")

        # Checking whether all the commands have been executed.
        while not self.matlab_process.poll():
            output_line = self.matlab_process.stdout.readline()
            sys.stdout.write(output_line)
            sys.stdout.flush()
            if str(output_line).find("CALTECH101_DONE") != -1:
                break

        # Double check if the category output file was really created and it is nonempty.
        if not (os.path.isfile(outputfile) and os.path.getsize(outputfile) > 0):
            raise Exception("Category output file was not created or was empty!")

    def stop_matlab_process(self):
        # kill matlab
        if self.matlab_process and not self.matlab_process.poll():
            self.matlab_process.stdin.write("quit()\n")
            self.matlab_process.kill()

if __name__ == "__main__":
    extractor = Caltech101()
    extractor.start()
    extractor.stop_matlab_process()
