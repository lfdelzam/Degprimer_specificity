import os
import re

#workflow for primers specificity

#-----DATA ---names-----------------------------------------------------------
configfile: "./support_files/primers_config.json"
workdir: config["workdir"]
thrs = config["threads"]
dir=config["database"]
list_of_primer_names=config["primer"]
seqf=config["seqf"]
namef=config["primer"]+"_"+config["namef"]
seqR=config["seqr"]
namer=config["primer"]+"_"+config["namer"]
Results=config["output_dir_name"]
ev=re.sub('-', '_', config["blast_params"])
ev=re.sub(' ','', ev)
ev=re.sub('_+', '_', ev)
ev=re.sub("'","", ev)
params_dir="id_"+config["identity"]+"_QC_"+config["Query_cov"]+ev
blast_dbname=os.path.basename(dir).split(".")[0]
if len(config["list_of_special_spps"]) == 0:
  lista = "''"
else:
  lista = config["list_of_special_spps"]
#------------------

rule all:
  input: expand("{Results}/{params_dir}/{name1}_{name2}_hits_selected", Results=Results, params_dir=params_dir, name1=namef, name2=namer),
         expand("{Results}/Spp_and_strains.txt", Results=Results), expand("{Results}/amplicons/{name1}_{name2}_amplicons.fna", Results=Results, name1=namef, name2=namer),
         expand("{Results}/krona/{name1}_{name2}_all_amplicons.html", Results=Results, name1=namef, name2=namer),
         expand("{Results}/krona/{name1}_{name2}_unique_amplicons.html", Results=Results, name1=namef, name2=namer)

rule Parsing_db:
   input: dir
   output: expand("{Results}/Spp_and_strains.txt", Results=Results)
   threads: thrs
   params: config["selected_genus"].capitalize()
   message: "Parsing sequences"
   shell: "python src/parse_genomes.py -i {input} -o {output} -g {params}"


rule undegenerator:
   output: t=expand("Primer/{name}{type}.fasta", zip, name=[namef, namer], type=["forward", "reverse"]),
           b=expand("Primer/{name1}_{name2}.fasta", name1=namef, name2=namer)
   params: seqf=seqf, namef=namef, seqR=seqR, namer=namer, outdir=config["workdir"]+"/"+"Primer"
   message: "undegenerating primers  -f {params.seqf} -F {params.namef} -r {params.seqR} -R {params.namer}"
   shell: "python src/undegenerator.py -f {params.seqf} -F {params.namef} -r {params.seqR} -R {params.namer} -o {params.outdir}"

rule blast:
  input: q=expand("Primer/{name1}_{name2}.fasta", name1=namef, name2=namer) #,
  output: expand("{Results}/BlastnEv{ev}/{name1}_{name2}vsNtdb.blastn", Results=Results, ev=ev, name1=namef, name2=namer)
  params: b=config["blast_params"], db="blast_db/"+blast_dbname+"/Ntdb", r=config["blast_output_option"]
  threads: thrs
  message: "Running blast"
  shell: "blastn -query {input.q} -db {params.db} {params.r} -out {output} -num_threads {threads} {params.b}"

rule parse_blast:
  input: expand("{Results}/BlastnEv{ev}/{name1}_{name2}vsNtdb.blastn", Results=Results, ev=ev, name1=namef, name2=namer)
  output: selected=expand("{Results}/{params_dir}/{name1}_{name2}_hits_selected", Results=Results, params_dir=params_dir,name1=namef, name2=namer),
          all=expand("{Results}/{params_dir}/{name1}_{name2}_hits", Results=Results, params_dir=params_dir,name1=namef, name2=namer)
  params: i=config["identity"], out=Results+"/"+params_dir+"/"+namef+"_"+namer+"_hits", id=config["primer"],
          l=config["Query_cov"], seqf=seqf, seqR=seqR, nf=namef, nr=namer
  message: "Printing out selected hits"
  shell: "python src/parse_blast.py -i {input} -d {params.i} -o {params.out} -n {params.id} -l {params.l} -f {params.seqf} -r {params.seqR} -F {params.nf} -R {params.nr}"

rule amplicons:
  input: db=expand("{Results}/BlastnEv{ev}/{name1}_{name2}vsNtdb.blastn", Results=Results, ev=ev, name1=namef, name2=namer),
         q=expand("Primer/{name1}_{name2}.fasta", name1=namef, name2=namer),
         fa=dir
  output: h=expand("{Results}/amplicons/{name1}_{name2}_amplicons.txt", Results=Results, name1=namef, name2=namer),
          a=expand("{Results}/amplicons/{name1}_{name2}_amplicons.fna", Results=Results, name1=namef, name2=namer),
          t=expand("{Results}/krona/{name1}_{name2}_all_amplicons_krona.tsv", Results=Results, name1=namef, name2=namer),
          u=expand("{Results}/krona/{name1}_{name2}_unique_amplicons_krona.tsv", Results=Results, name1=namef, name2=namer)
  params: M=int(config["Max_ampl_size"]), m=int(config["min_ampl_size"]), k=Results+"/krona/"+namef+"_"+namer,
          G=config["selected_genus"].capitalize(), S=lista
  message: "Calculating the number of amplicons"
  shell: "python src/parse_blast_amplicons.py -i {input.db} -p {input.q} -c {input.fa} -o {output.h} -a {output.a} -M {params.M} -m {params.m} -k {params.k} -g {params.G} -s {params.S}"

rule krona:
  input: t=expand("{Results}/krona/{name1}_{name2}_all_amplicons_krona.tsv", Results=Results, name1=namef, name2=namer),
         u=expand("{Results}/krona/{name1}_{name2}_unique_amplicons_krona.tsv", Results=Results, name1=namef, name2=namer)
  output: t=expand("{Results}/krona/{name1}_{name2}_all_amplicons.html", Results=Results, name1=namef, name2=namer),
          u=expand("{Results}/krona/{name1}_{name2}_unique_amplicons.html", Results=Results, name1=namef, name2=namer)
  message: "Krona charts"
  shell: '''
            ktImportText {input.t} -o {output.t}
            ktImportText {input.u} -o {output.u}
         '''
