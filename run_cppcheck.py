import argparse
import teamcity
import os
import subprocess
import re

def get_cppcheck_path():
    #if os.environ.get("ProgramFiles(x86)") is not None:
    #    return os.path.join(os.environ["ProgramFiles(x86)"], "cppcheck", "cppcheck.exe")
    #else:
        return os.path.join(os.environ["ProgramFiles"], "cppcheck", "cppcheck.exe")

def create_argument(arg_name, file_handle):
    def handler(line):
        return " " + arg_name + line.strip('\n')
    return "".join([handler(x) for x in file_handle.readlines()])

def create_exclude_paths_argument(file_handle):
    return create_argument("-i", file_handle)

def create_exclude_defines_argument(file_handle):
    return create_argument("-U", file_handle)

def create_include_defines_argument(file_handle):
    return create_argument("-D", file_handle)

def create_include_paths_argument(file_handle):
    return create_argument("", file_handle)

def handle_output_line(line):
    if line != "":
        line = line.strip('\n')
        m = re.search("^(##teamcity[^']*\s+description=')(.*)('[^']*)$", line)
        if m is None:
            print(line)
        else:
            escaped = re.sub("(['|\[\]])", "|\\1", m.group(2))
            print(m.group(1) + escaped + m.group(3))
        return True
    else:
        return False

def main():
    parser = argparse.ArgumentParser(description="Run cppcheck")
    parser.add_argument("--ac", type=str, help="Additional checks (default all)", default="all")
    parser.add_argument("--idir", type=str, help="Path of file with all include directories", default="include_directories.txt")
    parser.add_argument("--ip", type=argparse.FileType("r"), help="Path of file with directories to analyze", default="include_paths.txt")
    parser.add_argument("--idef", type=argparse.FileType("r"), help="Path of file with included definitions", default="include_defines.txt")
    parser.add_argument("--xp", type=argparse.FileType("r"), help="Path of file with directories or files to exclude from analysis", default="exclude_paths.txt")
    parser.add_argument("--xdef", type=argparse.FileType("r"), help="Path of file with definitions to exclude", default="exclude_defines.txt")
    parser.add_argument("--s", type=str, help="Path of file with warnings to suppress", default="suppressions.txt")
    parser.add_argument("--ot", type=str, help="The output template", default=None)
    parser.add_argument("--ext", type=str, help="Direct cppcheck arguments", default=None)

    # get all data from command line
    args = parser.parse_args()

    # if the output format is None identify whether under TC or not and set message format accordingly
    # if format set to TC will also need to escape messages
    if args.ot is None:
        if teamcity.is_running_under_teamcity():
            args.ot = "tc"
        else:
            args.ot = "vs"

    arguments = " --inline-suppr --error-exitcode=-1 --inconclusive --force" + \
                " --enable=" + args.ac + \
                ("" if args.ext is None else " " + args.ext) + \
                create_exclude_defines_argument(args.xdef) + \
                create_include_defines_argument(args.idef) + \
                create_include_paths_argument(args.ip) + \
                " --includes-file=" + args.idir + \
                create_exclude_paths_argument(args.xp) + \
                " --template=" + ('"##teamcity[buildProblem description=\'{file}:{line}: {severity} ({id}): {message}\']"' if args.ot == "tc" else args.ot) + \
                " --suppressions-list=" + args.s

    # run the process and redirect both stdout and stderr for further processing if needed
    if args.ot == "tc":
        process = subprocess.Popen(get_cppcheck_path() + arguments, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        while True:
            more = handle_output_line(process.stdout.readline().decode())
            if not more:
                break
        return process.returncode
    else:
        return subprocess.call(get_cppcheck_path() + arguments)

if __name__ == "__main__":
    main()
