import sys
import os
import subprocess
import argparse
import traceback

try:
    from Bio import SeqIO
except ImportError as e:
    print(e)
    sys.exit("ERROR...unable to load required python modules\ntry reinstalling and/or activating TIDAL environment:\n\tconda env create -f TIDAL.yml --name TIDAL\n\tconda activate TIDAL\n")


class Insertion:
    def __init__(self):
        self.info = {}
        self.is_ref = False


def main():
    code_dir = os.path.dirname(os.path.abspath(__file__))
    print(code_dir)
    args = parse_args()
    args = setup_input_files(args)
    chrom_len_file = make_chrom_files(args)
    read_length = estimate_read_length(args.fastq)
    depletion_tbl, insertion_tbl  = run_tidal(args, chrom_len_file, read_length, code_dir)
    write_output(depletion_tbl, insertion_tbl, args.sample_name, args.out)


def parse_args():
    parser = argparse.ArgumentParser(prog='TIDAL', description="Pipeline built to identify Transposon Insertion and Depletion in flies")

    ## required ##
    parser.add_argument("-f", "--fastq", type=str, help="A FASTQ file containing the NGS reads", required=True)
    parser.add_argument("-r", "--reference", type=str, help="A reference genome sequence in fasta format", required=True)
    parser.add_argument("-c", "--consensus", type=str, help="The consensus sequences of the TEs in fasta format", required=True)
    parser.add_argument("-a", "--annotation", type=str, help="The RefSeq annotation from UCSC genome browser", required=True)
    parser.add_argument("-g", "--gem", type=str, help="The gem mappability file for use with FREEC", required=True)
    parser.add_argument("-v", "--virus", type=str, help="Manunally curated sequence from fly viruses, structural and repbase sequences", required=True)
    parser.add_argument("-m", "--masked", type=str, help="A reference genome sequence in fasta format masked by RepeatMasker", required=True)
    parser.add_argument("-n", "--repeatmasker", type=str, help=" Repeat masker track from UCSC genome browser (table browser, track: Repeatmasker, table: rmsk, output format: all fields from table)", required=True)
    parser.add_argument("-t", "--table", type=str, help="Custom table for repbase to flybase lookup", required=True)

    parser.add_argument("-p", "--processors", type=int, help="Number of CPU threads to use for compatible tools (default=1)", required=False)
    parser.add_argument("-s", "--sample_name", type=str, help="Sample name to use for output files (default=FASTQ name)", required=False)
    parser.add_argument("-o", "--out", type=str, help="Directory to create the output files (must be empty/creatable)(default='.')", required=False)

    args = parser.parse_args()

    args.fastq = get_abs_path(args.fastq)
    args.reference = get_abs_path(args.reference)
    args.consensus = get_abs_path(args.consensus)
    args.annotation = get_abs_path(args.annotation)
    args.gem = get_abs_path(args.gem)
    args.virus = get_abs_path(args.virus)
    args.masked = get_abs_path(args.masked)
    args.repeatmasker = get_abs_path(args.repeatmasker)
    args.table = get_abs_path(args.table)

    if args.sample_name is None:
        args.sample_name = os.path.basename(args.fastq)
        args.sample_name = ".".join(args.sample_name.split(".")[:-1])
    else:
        if "/" in args.sample_name:
            sys.exit(args.sample_name+" is not a valid sample name...\n")
    
    if args.processors is None:
        args.processors = 1

    if args.out is None:
        args.out = os.path.abspath(".")
    else:
        args.out = os.path.abspath(args.out)
        try:
            mkdir(args.out)
        except Exception as e:
            track = traceback.format_exc()
            print(track, file=sys.stderr)
            print("cannot create output directory: ",args.out,"exiting...", file=sys.stderr)
            sys.exit(1)

    return args


def mkdir(indir, log=None):
    if os.path.isdir(indir) == False:
        os.mkdir(indir)

def remove_file_ext(infile):
    no_ext = ".".join(infile.split(".")[:-1])
    return no_ext

def get_abs_path(in_file, log=None):
    if os.path.isfile(in_file):
        return os.path.abspath(in_file)
    else:
        msg = " ".join(["Cannot find file:",in_file,"exiting....\n"])
        sys.stderr.write(msg)
        sys.exit(1)

def get_base_name(path):
    no_path = os.path.basename(path)
    if no_path[-3:] == ".gz":
        no_path = no_path[:-3]
    no_ext = ".".join(no_path.split(".")[:-1])

    return no_ext

def copy(infile, outdir, outfilename=None):
    if outfilename is None:
        outfile = outdir+"/"+os.path.basename(infile)
    else:
        outfile = outdir+"/"+outfilename
    subprocess.call(["cp", infile, outfile])
    return outfile

def run_command(cmd_list, log=None, fatal=True):
    msg = ""
    if log is None:
        try:
            subprocess.check_call(cmd_list)
        except subprocess.CalledProcessError as e:
            if e.output is not None:
                msg = str(e.output)+"\n"
            if e.stderr is not None:
                msg += str(e.stderr)+"\n"
            cmd_string = " ".join(cmd_list)
            msg += msg + cmd_string + "\n"
            sys.stderr.write(msg)
            if fatal:
                sys.exit(1)
            else:
                return False
    
    else:
        try:
            out = open(log,"a")
            out.write(" ".join(cmd_list)+"\n")
            subprocess.check_call(cmd_list, stdout=out, stderr=out)
            out.close()

        except subprocess.CalledProcessError as e:
            if e.output is not None:
                msg = str(e.output)+"\n"
            if e.stderr is not None:
                msg += str(e.stderr)+"\n"
            cmd_string = " ".join(cmd_list)
            msg += msg + cmd_string + "\n"
            writelog(log, msg)
            sys.stderr.write(msg)
            if fatal:
                sys.exit(1)
            else:
                return False
    
    return True

def writelog(log, msg):
    if log is not None:
        with open(log, "a") as out:
            out.write(msg)

def setup_input_files(args):
    ref_dir = args.out+"/reference"
    mkdir(ref_dir)
    os.chdir(ref_dir)
    args.reference = copy(args.reference, ref_dir)
    args.consensus = copy(args.consensus, ref_dir)
    args.annotation = copy(args.annotation, ref_dir)
    args.gem = copy(args.gem, ref_dir)
    args.virus = copy(args.virus, ref_dir)
    args.masked = copy(args.masked, ref_dir, outfilename="masked."+ get_base_name(args.masked))
    args.repeatmasker = copy(args.repeatmasker, ref_dir)
    args.table = copy(args.table, ref_dir)

    run_command(["bowtie-build", args.virus, get_base_name(args.virus)])

    run_command(["bowtie-build", args.consensus, get_base_name(args.consensus)])
    run_command(["bowtie2-build", args.consensus, get_base_name(args.consensus)])

    run_command(["bowtie-build", args.reference, get_base_name(args.reference)])
    run_command(["bowtie2-build", args.reference, get_base_name(args.reference)])
    run_command(["bowtie-build", args.masked, get_base_name(args.masked)])

    mkdir(args.out+"/TIDAL_out")
    if args.fastq[-3:] == ".gz":
        args.fastq = copy(args.fastq, args.out+"/TIDAL_out", outfilename=args.sample_name+".fastq.gz")
        run_command(["gunzip", args.out+"/TIDAL_out/"+args.sample_name+".fastq.gz"])
        args.fastq = args.fastq[:-3]
    else:
        args.fastq = copy(args.fastq, args.out+"/TIDAL_out", outfilename=args.sample_name+".fastq")
    
    return args


def make_chrom_files(args):
    mkdir(args.out+"/reference/chroms")
    chrom_len_file = args.out+"/reference/chrom_lengths.tsv"
    with open(args.reference, "r") as infa, open(chrom_len_file,"w") as out_lens:
        for record in SeqIO.parse(infa, "fasta"):
            seq_name = str(record.id)
            seq_len = len(str(record.seq))
            out_lens.write(seq_name+"\t"+str(seq_len)+"\n")

            chrom_file = args.out+"/reference/chroms/"+seq_name+".fa"
            with open(chrom_file,"w") as outfa:
                outfa.write(">"+seq_name+"\n")
                outfa.write(str(record.seq)+"\n")
    
    return chrom_len_file


def estimate_read_length(fq, reads=10000):
    lengths = []
    with open(fq,"r") as f:
        for x, line in enumerate(f):
            if x%4 == 1:
                lengths.append(len(line.replace('\n',"")))
            
            if x >= reads:
                break
    
    length = sum(lengths)//len(lengths)

    return length

def run_tidal(args, chrom_len, read_length, codedir):
    os.chdir(args.out+"/TIDAL_out")

    run_command(["bash", codedir+"/data_prep.sh", os.path.basename(args.fastq), codedir, str(args.processors)])

    if not os.path.exists(os.path.basename(args.fastq)+".uq.polyn"):
        sys.exit("data_prep.sh failed...exiting...\n")

    run_command([
        "bash", codedir+"/insert_pipeline.sh",
            os.path.basename(args.fastq)+".uq.polyn",
            str(read_length),
            codedir,
            remove_file_ext(args.reference),
            remove_file_ext(args.masked),
            remove_file_ext(args.consensus),
            args.reference,
            args.annotation,
            chrom_len,
            args.out+"/reference/chroms/",
            args.gem,
            remove_file_ext(args.virus),
            args.consensus,
            str(args.processors)
    ])

    if not os.path.exists(args.out+"/TIDAL_out/insertion/"+args.sample_name+"_Inserts_Annotated.txt"):
        sys.exit("insert_pipeline.sh failed...exiting...\n")

    run_command(["bash", codedir+"/setup.sh", os.path.basename(args.fastq)])

    run_command([
        "bash", codedir+"/depletion_pipeline.sh",
            os.path.basename(args.fastq)+".uq.polyn",
            str(read_length),
            codedir,
            remove_file_ext(args.reference),
            remove_file_ext(args.masked),
            remove_file_ext(args.consensus),
            args.reference,
            args.masked,
            args.repeatmasker,
            args.annotation,
            args.table,
            chrom_len,
            str(args.processors)
    ])

    if not os.path.exists(args.out+"/TIDAL_out/depletion/"+args.sample_name+"_Depletion_Annotated.txt"):
        sys.exit("insert_pipeline.sh failed...exiting...\n")

    run_command(["bash", codedir+"/last_part.sh", os.path.basename(args.fastq), codedir])

    if not os.path.exists(args.out+"/TIDAL_out/"+args.sample_name+"_result/"+args.sample_name+"_Depletion_Annotated.txt"):
        sys.exit("last_part.sh failed...exiting...\n")

    depletion_table = args.out+"/TIDAL_out/"+args.sample_name+"_result/"+args.sample_name+"_Depletion_Annotated_TEonly.txt"
    insertion_table = args.out+"/TIDAL_out/"+args.sample_name+"_result/"+args.sample_name+"_Inserts_Annotated.txt"

    return depletion_table, insertion_table 


def write_output(depletion_tbl, insertion_tbl, sample_name, out_dir):

    insertions = []
    with open(insertion_tbl,"r") as tbl:
        for x,line in enumerate(tbl):
            if x == 0:
                headers = line.replace("\n","").split("\t")
            else:
                insert = Insertion()
                split_line = line.replace("\n","").split("\t")
                for x,val in enumerate(split_line):
                    insert.info[headers[x]] = val
                
                insertions.append(insert)

    with open(out_dir+"/TIDAL_out/"+sample_name+"_result/"+sample_name+"_TIDAL_tmp.bed", "w") as outbed:
        outbed.write('track name="'+sample_name+'_popoolationte" description="'+sample_name+'_popoolationte"\n')

        for x,insert in enumerate(insertions):
            if not insert.is_ref:
                name = insert.info['TE']+"|non-reference|"+insert.info['Coverage_Ratio']+"|"+sample_name+"|sr|"+str(x)
                out_line = [insert.info["Chr"], insert.info["Chr_coord_5p"], insert.info["Chr_coord_3p"], name, "0", "."]

                outbed.write("\t".join(out_line) + "\n")




if __name__ == "__main__":                
    main()