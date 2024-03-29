#!/usr/bin/env python3

import os
import argparse
import re

usage = 'parse_blast_amplicons.py -i -p -r -d -l -M -m -o -a -k -g -s'
description = 'This program prints the predicted amplicons from primers'

parser = argparse.ArgumentParser(description=description, usage=usage)
parser.add_argument(
    '-i',
    dest='inf',
    help='input file .blastn', required=True)
parser.add_argument('-p', dest='p', help='primers fasta file',
                    required=True)
parser.add_argument(
    '-c',
    dest='c',
    help='Input fasta (non-interleave) file, complete sequences ',
    required=True)
parser.add_argument(
    '-d', dest='d', help='identity threshold default 100', default=100)
parser.add_argument(
    '-l',
    dest='l',
    help='percentage query coverage threshold (default 100)',
    default=100)
parser.add_argument('-m', dest='m', help='min amplicon length (default 50)', default=50)
parser.add_argument(
    '-M',
    dest='M',
    help='Max amplicon length (default 1000)',
    default=1000)
parser.add_argument('-o', dest='o', help='output file, hits',
                    required=True)
parser.add_argument('-a', dest='a', help='output file .fna, amplicons',
                    required=True)
parser.add_argument(
    '-k',
    dest='k',
    help='prefix output file .tsv, krona',
    required=True)

parser.add_argument(
    '-g',
    dest='g',
    help='name of selected genus (default Vibrio)',
    default="Vibrio")

parser.add_argument(
    '-s',
    dest='s',
    help='List of selected species',
    default="cholerae,vulnificus,parahaemolyticus,alginolyticus,sp")

args = parser.parse_args()

def revcomp(line):
    old_chars = "ACGT"
    replace_chars = "TGCA"
    new = line.translate(line.maketrans(old_chars, replace_chars))[::-1]
    return new

def get_primer_seqs(file):
    seq = {}
    with open(file, "r") as fp:
        for line in fp:
            line = line.rstrip()
            if line.startswith(">"):
                clean = line[1:].replace(" ", "")
            else:
                seq[clean] = line
    return seq

def clean_name(name):
    name = re.sub(".chromosome.*$", "", name, count=1)
    name = re.sub(".genome.*$", "", name, count=1)
    name = re.sub(".plasmid.*$", "", name, count=1)
    name = re.sub(".DNA.*$", "", name, count=1)
    name = re.sub(".complete.*$", "", name, count=1)
    name = re.sub("sp.", "sp", name, count=1)
    name = re.sub(".contig.*$", "", name, count=1) #new

    return name

def get_selected_hits(file,seqs):

    hits = {}
    with open(file, "r") as fin:
        for line in fin:
            line = line.rstrip()
    # Fields: query acc., subject acc., % identity, alignment length, mismatches, gap opens, q. start, q. end, s. start, s. end, evalue, bit score
            if not line.startswith("#"):
                line = line.split()
                loci = line[1]
                id = loci.split("_")
                id = "_".join(id[2:])
                id=clean_name(id)
                identity = float(line[2])
                align_len = float(line[3])
                pn = line[0]
                start = line[8]
                stop = line[9]
                primer_len = len(seqs[pn])
                p_align = round(align_len / primer_len * 100, 2)
                if p_align >= float(args.l) and identity >= float(args.d):
                    if loci in hits:
                        if id in hits[loci]:
                            hits[loci][id].append((pn, start, stop))
                        else:
                            hits[loci] = {id: [(pn, start, stop)]}

                    else:
                        hits[loci] = {id: [(pn, start, stop)]}
    return hits


def update_dict(g,s,t,dictn):
    if g in dictn:
        if s in dictn[g].keys():
            if t in dictn[g][s].keys():
                dictn[g][s][t] += 1
            else:
                dictn[g][s][t] = 1
        else:
            dictn[g][s] = {t: 1}
    else:
        dictn[g] = {s: {t: 1}}

    return dictn


def fwd_revs_info(primer_loc):
    revs = set()
    forws = set()
    for p_inf in primer_loc:
        if re.search("reverse", p_inf[0]):
            revs.add(p_inf)
        else:
            forws.add(p_inf)
    return revs, forws


def from_to(primer1,primer2):
    a = int(primer1[1])
    b = int(primer1[2])
    c = int(primer2[1])
    if a < b:
        direct = "+"
        fro = a
        to = c
    else:
        direct = "-"
        fro = c
        to = a
    return fro, to, direct


def analyse_and_print_out_hits(file, hits, selected_genus):

    Gs_sps = {}
    strns = set()
    alg = []
    t_amplicons = 0
    slctd_hits = {}
    with open(file, "w") as fout:
        for l in hits:
            for i in hits[l]:
                rev, forw=fwd_revs_info(hits[l][i])
                for q in forw:
                    for w in rev:
                        if q and w:
                            sta,sto,direction=from_to(q,w)
                            amplicon_length = sto - sta
                            if (amplicon_length >= int(args.m)
                                    and amplicon_length <= int(args.M)):

                                gns = i.split("_")[0]  # Vibrio
                                sps = i.split("_")[1]  # parahaemolyticus
                                strs = "_".join(i.split("_")[2:]) # strain_FDAARGOS_667
                                Gs_sps=update_dict(gns,sps,strs,Gs_sps)
                                if gns == selected_genus:
                                    t_amplicons += 1
                                    strns.add(i)
                                    alg.append(amplicon_length)

                                if l in slctd_hits:
                                    slctd_hits[l].append((direction, sta, sto))
                                else:
                                    slctd_hits[l] = [(direction, sta, sto)]

                                print("*** Strain: {} - Loci: {}".format(i, l), file=fout)
                                print("forward {} - reverse {} - amplicon length {} - direction {} - start {} - stop {}".format(q, w, amplicon_length, direction, sta, sto), file=fout)
        if len(alg) > 0:
            print("#            From genus {}: Total amplicons {} - species {} - strains {}".format(selected_genus, t_amplicons, len(Gs_sps["Vibrio"].keys()), len(strns)), file=fout)
            print("#                Avg amplicon size {} Max {} Min {}".format(round(sum(alg) / len(alg), 1), max(alg), min(alg)), file=fout)
        else:
            print("#            From genus {}: Total amplicons {} - species {} - strains {}".format(selected_genus, t_amplicons, 0, 0), file=fout)

    return alg, t_amplicons, Gs_sps, strns, slctd_hits

def stdout_selected_genus_results(total_sp_identyf_strn, total_sp_identyf_sp, genus_selected, selected_genus, selected_sps):
    print(
        "#                From genus {}: Total number of strains 100% identifiable: {} strains from {} species".format(selected_genus,
            len(total_sp_identyf_strn),
            len(total_sp_identyf_sp)))
    if selected_sps[0] != "" :
        print("#                    particularly,")
        for spe in selected_sps:
            if spe in genus_selected[selected_genus].keys():
                print("#                                {} {} strains".format(spe,
                    len(genus_selected[selected_genus][spe].keys())))
            else:
                print("#                                {} 0 strain".format(spe))
    print("Identifiable {} strains: {}".format(selected_genus,",".join(total_sp_identyf_strn)))


def update_seqs_uniq(hdr, toprint, uniq):

    strnam = hdr.split("_")
    strnam = "_".join(strnam[2:])
    strnam = strnam.split()[0]
    if toprint in uniq:
        uniq[toprint].append((strnam))
    else:
        uniq[toprint] = [(strnam)]

    return uniq

def extract_records(identifiable_strains, selected_genus):
    Genus_id = {}
    total_identyf_sp = set()
    total_identyf_strn = set()
    for sro in identifiable_strains:
        gens = sro.split("_")[0]
        spes = sro.split("_")[1]
        strais = "_".join(sro.split("_")[2:])
        if gens == selected_genus:
            total_identyf_sp.add(spes)
            total_identyf_strn.add(gens + "_" + spes + "_" + strais)

        Genus_id=update_dict(gens,spes,strais,Genus_id)

    return Genus_id, total_identyf_sp, total_identyf_strn


def print_out_counters(genus,fileout, selected_genus):

    cont_g = 0
    cont_sp = 0
    cont_str = 0
    for gn in genus:
        if gn != selected_genus:
            cont_g += 1
            for sp in genus[gn]:
                cont_sp += 1
                for s in genus[gn][sp]:
                    cont_str += 1
                    print("{}\t{}\t{}\t{} {} {}".format(genus[gn][sp][s], gn, sp, gn, sp, s), file=fileout)
        else:
            for sp in genus[gn]:
                for s in genus[gn][sp]:
                    print("{}\t{}\t{}\t{} {} {}".format(genus[gn][sp][s], gn, sp, gn, sp, s), file=fileout)

    return cont_g, cont_sp, cont_str


primers_seq=get_primer_seqs(args.p)
id_hit=get_selected_hits(args.inf,primers_seq)
al, total_amplicons, G_species, strains, selected_hits= analyse_and_print_out_hits(args.o, id_hit, args.g)

if len(al) > 0:
    print(
        "#                From genus {}: Total amplicons {} - species {} - strains {}".format(args.g,
            total_amplicons, len(
                G_species[args.g].keys()), len(strains)))
    print("#                    Avg amplicon size {} Max {} Min {}".format(
        round(sum(al) / len(al), 1), max(al), min(al)))


with open(args.c, "r") as fc, open(args.a, "w") as fam, open(args.k + "_all_amplicons_krona.tsv", "w") as fk, open(args.k + "_unique_amplicons_krona.tsv", "w") as fku:
    if len(selected_hits.keys()) > 0:

        seq_uniq = {}
        copy = False
        for line in fc:
            line = line.rstrip()
            if line.startswith(">"):
                h = line.split()[0][1:]
                if h in selected_hits:
                    header=clean_name(line)
                    header += " [direction +]"
                    k = h
                    copy = True
            else:
                if copy:
                    for item in selected_hits[k]:
                        ini = int(item[1]) - 1
                        final = int(item[2])
                        head = header + "[length=" + str(final - ini) + "]"
                        if item[0] == "+":
                            print(head, file=fam)
                            seqprint = line[ini:final]
                            print(seqprint, file=fam)
                            seq_uniq= update_seqs_uniq(head, seqprint, seq_uniq)

                        else:
                            print(head, file=fam)
                            seqtoprint = revcomp(line[ini:final])
                            print(seqtoprint, file=fam)
                            seq_uniq= update_seqs_uniq(head, seqtoprint, seq_uniq)

                        copy = False

        print("#            Total number of unique sequences (100% identity, same size): {}".format(len(seq_uniq.keys())), file=fam)
        print("#                Total number of unique sequences (100% identity, same size): {}".format(
            len(seq_uniq.keys())))

        identifiable_strain = set()
        for names in seq_uniq.values():
            if len(names) == 1:
                identifiable_strain.add(names[0])

        Genus, total_vibrio_identyf_sp, total_vibrio_identyf_strn=extract_records(identifiable_strain, args.g)

        if args.g in Genus.keys():
            stdout_selected_genus_results(total_vibrio_identyf_strn, total_vibrio_identyf_sp, Genus, args.g, args.s.split(","))

        print("         -------------------------------------")
        conta_g, conta_sp, conta_str=print_out_counters(Genus,fku, args.g)

        print(
            "# 100% identifiable amplicons that are not {}: Genus {} Spp {} strains {}".format(args.g,
                conta_g,
                conta_sp,
                conta_str))

        contador_g, contador_sp, contador_str=print_out_counters(G_species,fk, args.g)

        print(
            "# Number of amplicons that are not {}: Genus {} Spp {} strains {}".format(args.g,
                contador_g,
                contador_sp,
                contador_str))
        if contador_g > 0:
            print("    where, genus (exluding {}) are: {}".format(args.g,
                ",".join([g for g in G_species.keys() if g != args.g])))

        print("         -------------------------------------")

    else:
        print("#            no amplicons finds or amplicon size longer/smaller than threshold ({},{})".format(args.m, args.M))
        print("#            no amplicons finds or amplicon size longer/smaller than threshold ({},{})".format(args.m, args.M), file=fam)
