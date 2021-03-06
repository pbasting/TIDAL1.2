#!/usr/bin/perl
use strict;
use warnings;
use Getopt::Std;


#variaable
# 1. Genome sequence
# /nlmusr/gchirn/linux/UCSC_GENOME/fly/ucsc_fly_genome

# level 1 cluster file
# Threshold how much to include on either side of the cluster
#
# if we did the sam file approach, then find reads that fall between start - (ennd + 22)
my ($genome_file, $cluster_file, $LIMIT);
$LIMIT=100;
my $SEQ_BUFFER=22;

my %option;
getopts( 'g:c:l:h', \%option );
if (( $option{g} ) && ( $option{c} ) && ( $option{l} ) ) {
    $LIMIT = $option{l};
    $genome_file = $option{g};
    $cluster_file = $option{c};
}

#if want to use the code without any buffer
if ($LIMIT==1) {
$LIMIT=0;	
}

#$LIMIT= int ($LIMIT/2);

my $g_hash = {};
my $c_hash = {}; #add the limit before coordinates are loaded. 
# insertion number is key, and chr:start:end is the value


#acutally upload the genome first, that way I just have to loop over the cluster file only once...


#read fasta file, and return a hash
#my $genome_file$input_filename = $ARGV[0];


$g_hash = &process_fastafile($genome_file);
#now read the cluster file

my $arr2d=[];
open(my $INFILE, "<", $cluster_file) 
        or die "unable to open ct file $cluster_file";
while ( my $line = <$INFILE> ) {
    chomp $line;
    if ($line=~/^SV/) {
#	$first_line = $line;
	next;
    }
    my @arr = split(/\t/, $line);
    push @{$arr2d}, \@arr;

}
my @sortarr = sort { ($a->[1] cmp $b->[1]) || ($a->[2] <=> $b->[2]) } @{$arr2d};

my ($insert_number, $chr, $chr_start, $chr_end, $read_number);

foreach my $line ( @sortarr ) {
    
    $insert_number=$line->[0];
    $chr=$line->[1];
    $chr_start= $line->[2];
    $chr_end=$line->[3];
    $read_number = $line->[7];

    my $seq_start = $chr_start-$LIMIT;
    my $seq_end =  $chr_end+$LIMIT+$SEQ_BUFFER;
    my $seq_length = $seq_end - $seq_start + 1; 


#now retrieve the sequence from the chromosome
    my $chr_seq = $g_hash->{$chr} ;
    my $seq_segment = substr($chr_seq, $seq_start, $seq_length);
 

    my $fasta_output = ">$insert_number=$seq_length :$chr:$chr_start:$chr_end\n$seq_segment\n";
    print "$fasta_output";
#    die;
}





exit;

sub process_fastafile {
    my ($fafilename) = @_;
    my ($fa_hash) = {};
    
    my $input_filename = $fafilename;
    open(my $INFILE, "<", $input_filename) 
        or die "unable to open ct file $input_filename";
    
    
    my ($first_part, $second_part) = ("", "");
    while ( my $line = <$INFILE> ) {
        
        if ( $line =~ /^>/) {
            
            unless ( $first_part eq '') {
                $fa_hash->{$first_part} = $second_part;
                
                #$seq =~ s/[\n\s\t\r\W]//g; #should I remove other unwanted characters?
                
                ($first_part, $second_part) = ("", "");
            }

            chomp $line;
            # print "header: $line\n"; remove ">"
            my $foo = reverse($line);
            chop($foo);
            $first_part = reverse($foo);
            
        } else {
            # print $line;
	    chomp $line;
            $second_part .= $line; 
        }
    }
    
    $fa_hash->{$first_part} = $second_part;    
    return ($fa_hash);    
}
