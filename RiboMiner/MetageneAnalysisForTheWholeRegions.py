#!/usr/bin/env python
# -*- coding:UTF-8 -*-
'''
@Author: Li Fajin
@Date: 2019-08-14 10:47:05
@LastEditors: Li Fajin
@LastEditTime: 2019-10-22 15:29:26
@Description:
		This script is used for metagene analysis along the whole transcripts
		usage: python MetageneAnalysisForTheWholeRegions.py -i 1.bam,2.bam -o test -c longest.trans.info.txt -r 28,29,30_27,28,29 -s 12,12,12_12,12,12 -t bamFile1,bamFile2 -b 15,90,60
				-l 150 (codon) -m 1 -n 10 -e 30 -S selective_transcripts.txt --id-type transcript_id(default) --plot yes
			or python MetageneAnalysisForTheWholeRegions.py -f bamlistFile_attributes.txt -o test -c longest.trans.info.txt -b 15,90,60
				-l 150 (codon) -m 1 -n 10 -e 30 -S selective_transcripts.txt --id-type transcript_id(default) --plot yes
		input:
			1) bamFiles
			2) coordinate file (generated by generated by OutputTranscriptInfo.py)
			3) read length of reads
			4) offset of reads you selected
			5) bamFile legends
			6) bins you want to set, separated by comma, representing relative length of 5UTR, CDS, and 3UTR
			7) et, al.
		output:
			1) metagene results. dataframe format, total bins rows  and N columns. (total bins = 5UTR+CDS+3UTR, N = number of samples)
'''



from __future__ import division
from .FunctionDefinition import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns





def scale_transcripts_length(read_counts_vector,bin_number,Type=None):
    if Type == '5UTR': ## do not contain start codon
        bins=int(bin_number)
        steps=int(len(read_counts_vector)/bins)
        read_counts_vector_scaled=np.zeros(bins,dtype="float64")
        if len(read_counts_vector) <= bins:
            if len(read_counts_vector) == 0:
                read_counts_vector=read_counts_vector_scaled
            read_counts_vector_scaled[-len(read_counts_vector):]+=read_counts_vector
        else:
            tmp_read_counts_vector_scaled=[np.mean(read_counts_vector[i:(i+steps)]) for i in np.arange(0,len(read_counts_vector),steps)]
            read_counts_vector_scaled[:]+=tmp_read_counts_vector_scaled[:bins]
            read_counts_vector_scaled[-1]=np.mean(tmp_read_counts_vector_scaled[(bins-1):])
    if Type == "CDS":
        bins=int(bin_number)
        steps=int(len(read_counts_vector)/bins)
        read_counts_vector_scaled=np.zeros(bins,dtype="float64")
        if len(read_counts_vector) <= bins:
            raise IOError("The length of this script is less than 90nt")
        else:
            tmp_read_counts_vector_scaled=[np.mean(read_counts_vector[i:(i+steps)]) for i in np.arange(0,len(read_counts_vector),steps)]
            read_counts_vector_scaled[:]+=tmp_read_counts_vector_scaled[:bins]
            read_counts_vector_scaled[-1]=np.mean(tmp_read_counts_vector_scaled[(bins-1):])
            read_counts_vector_scaled=read_counts_vector_scaled/np.mean(read_counts_vector_scaled)
    if Type == "3UTR": ## do not contain stop codon
        bins=int(bin_number)
        steps=int(len(read_counts_vector)/bins)
        read_counts_vector_scaled=np.zeros(bins,dtype="float64")
        if len(read_counts_vector) <= bins:
            if len(read_counts_vector) == 0:
                read_counts_vector=read_counts_vector_scaled
            read_counts_vector_scaled[:len(read_counts_vector)]+=read_counts_vector
        else:
            tmp_read_counts_vector_scaled=[np.mean(read_counts_vector[i:(i+steps)]) for i in np.arange(0,len(read_counts_vector),steps)]
            read_counts_vector_scaled[:]+=tmp_read_counts_vector_scaled[:bins]
            read_counts_vector_scaled[-1]=np.mean(tmp_read_counts_vector_scaled[(bins-1):])
    return read_counts_vector_scaled

def NormedDensityCalculation(in_bamFile,in_selectTrans,in_transLengthDict,in_startCodonCoorDict,in_stopCodonCoorDict,inCDS_lengthFilterParma,inCDS_countsFilterParma,in_excludeLengthParma,in_excludeCodonCountsParma,in_readLengths,in_readOffset,Bins):
	pysamFile=pysam.AlignmentFile(in_bamFile,"rb")
	pysamFile_trans=pysamFile.references
	in_selectTrans=set(pysamFile_trans).intersection(in_selectTrans)
	passTransSet=set()
	Bins_vector=lengths_offsets_split(Bins)
	final_density_vector=np.zeros(np.sum(Bins_vector),dtype="float64")
	trans_density_scaled=[]
	filter_1=0
	filter_2=0
	filter_3=0
	filter_4=0
	filter_5=0
	all_counts=0
	for trans in in_startCodonCoorDict.keys():
		leftCoor =int(in_startCodonCoorDict[trans])-1
		rightCoor=int(in_stopCodonCoorDict[trans])-3
		(trans_counts,read_counts_frameSum,total_reads,cds_reads)=get_trans_frame_counts(pysamFile, trans, in_readLengths, in_readOffset, in_transLengthDict[trans], leftCoor, rightCoor)
		all_counts+=total_reads ## total_reads for transcript level
	for trans in in_selectTrans:
		leftCoor =int(in_startCodonCoorDict[trans])-1# the first position of start codon
		rightCoor=int(in_stopCodonCoorDict[trans])-3 ## the first position of stop codon
		if ((rightCoor-leftCoor) < inCDS_lengthFilterParma*3): # codon level
			filter_1+=1
			continue
		if (rightCoor-leftCoor)%3 !=0:
			filter_2+=1
			continue
		# get transNum and trans 5Pos offset counts vector
		(trans_counts,read_counts_frameSum,total_reads,cds_reads)=get_trans_frame_counts(pysamFile, trans, in_readLengths, in_readOffset, in_transLengthDict[trans], leftCoor, rightCoor)
		if total_reads==0 or in_transLengthDict[trans]==0:
			filter_3+=1
			continue
		trans_counts_density=10**6*(trans_counts/(all_counts))
		cds_reads_counts_density=10**9*(cds_reads/(all_counts*len(read_counts_frameSum)))
		if cds_reads_counts_density < inCDS_countsFilterParma: ## RPKM criteria
			filter_4+=1
			continue
		normValue=np.mean(trans_counts_density)
		sumValue=np.sum(read_counts_frameSum[int(in_excludeLengthParma):])
		sumValue_normed=10**9*(sumValue/(all_counts*len(read_counts_frameSum)))
		if normValue == 0 or sumValue_normed < in_excludeCodonCountsParma: ## RPKM criteria
			filter_5+=1
			continue
		trans_counts_density_normed=trans_counts_density/normValue
		Five_UTR_density=trans_counts_density_normed[:leftCoor] ## do not contain start codon
		cds_reads_density=trans_counts_density_normed[leftCoor:(rightCoor+3)] ## contain start codon and stop codon
		Three_UTR_density=trans_counts_density_normed[(rightCoor+3):] ## do not contain stop codon
		# print(trans,len(Five_UTR_density),len(cds_reads_density),len(Three_UTR_density))
		Five_UTR_density_scaled=scale_transcripts_length(Five_UTR_density,Bins_vector[0],Type="5UTR")
		cds_reads_density_scaled=scale_transcripts_length(cds_reads_density,Bins_vector[1],Type="CDS")
		Three_UTR_density_scaled=scale_transcripts_length(Three_UTR_density,Bins_vector[2],Type="3UTR")
		tmp_trans_reads_density_scaled=list(Five_UTR_density_scaled)+list(cds_reads_density_scaled)+list(Three_UTR_density_scaled)
		trans_density_scaled.append(tmp_trans_reads_density_scaled)
		passTransSet.add(trans)
	trans_density_scaled=np.array(trans_density_scaled)
	# print(trans_density_scaled.shape)
	for terms in range(np.sum(Bins_vector)):
		final_density_vector[terms]=np.mean(trans_density_scaled[:,terms])
	pysamFile.close()
	print("Lenght filter(-l)---Transcripts number filtered by criterion one is : "+str(filter_1),file=sys.stderr)
	print("Lenght filter (3n)---Transcripts number filtered by criterion two is : "+str(filter_2),file=sys.stderr)
	print("Total counts filter---Transcripts number filtered by criterion three is : "+str(filter_3),file=sys.stderr)
	print("CDS density filter(RPKM-n or counts-n)---Transcripts number filtered by criterion four is : "+str(filter_4),file=sys.stderr)
	print("CDS density filter(normed-m)---Transcripts number filtered by criterion five is : "+str(filter_5),file=sys.stderr)
	print("Metaplots Transcript Number for bam file"+in_bamFile+" is :"+str(len(passTransSet)),file=sys.stderr)
	return final_density_vector

def MetagenePLotForTheWholeRegions(data,bins,inOutPrefix):
	'''plot the density dsitribution'''
	samples=np.unique(data.columns)
	plt.rc('font',weight='bold')
	text_font={"size":20,"family":"Arial","weight":"bold"}
	legend_font={"size":20,"family":"Arial","weight":"bold"}
	fig=plt.figure(figsize=(10,6))
	ax=fig.add_subplot(111)
	bins_vector=lengths_offsets_split(bins)
	winLen=np.sum(bins_vector)
	if len(samples) <=8:
		colors=["b","orangered","green","c","m","y","k","w"]
	else:
		colors=sns.color_palette('husl',len(samples))
	for i in np.arange(len(samples)):
		plt.plot(np.arange(0,winLen),data.loc[:,samples[i]],color=colors[i],label=samples[i],linewidth=2)
	ax.set_xticks([])
	ax.axvline(int(bins_vector[0]),color='gray',dashes=(2,3),clip_on=False,linewidth=2)
	ax.axvline(int(bins_vector[0])+int(bins_vector[1]),color='gray',dashes=(2,3),clip_on=False,linewidth=2)
	ax.set_ylabel("Relative footprint density (AU)",fontdict=text_font)
	ax.set_xlabel("Normalized transcript length",fontdict=text_font,labelpad=30)
	ax.spines["top"].set_visible(False)
	ax.spines["right"].set_visible(False)
	ax.spines["bottom"].set_linewidth(2)
	ax.spines["left"].set_linewidth(2)
	ax.tick_params(which="both",width=2)
	plt.legend(loc="best",prop=legend_font)
	plt.tight_layout()
	# plt.subplots_adjust(left=0.125,right=0.9,bottom=0.15,top=0.9)
	plt.savefig(inOutPrefix+"_metagenePlot_forTheWholeRegions.pdf")
	plt.close()

def write_scaled_density_dataframe(inBamAttr,outFile):
	data=[]
	data_index=[]
	for bms in inBamAttr:
		d=bms.final_density_vector
		i=bms.bamLegend
		data.append(d)
		data_index.append(i)
	data=pd.DataFrame(data,index=data_index)
	data=data.T
	data.to_csv(outFile,sep="\t",index=None)
	return data

def main():
	parsed=create_parser_for_metagene_analysis_for_the_whole_regions()
	(options,args)=parsed.parse_args()
	if options.bamListFile and (options.bam_files or options.read_length or options.read_offset or options.bam_file_legend):
		raise IOError("'-f' parameter and '-i -r -s -t' are mutually exclusive.")
	if options.bamListFile:
		bamFiles,readLengths,Offsets,bamLegends=parse_bamListFile(options.bamListFile)
	elif options.bam_files:
		bamFiles,readLengths,Offsets,bamLegends=options.bam_files.split(","),options.read_length.split("_"),options.read_offset.split("_"),options.bam_file_legend.split(",")
	else:
		raise IOError("Please check you input files!")
	if len(options.bins.strip().split(',')) !=3:
		raise IOError("Please check your -b parameters! It must have three numbers separated by comma. e.g. '15,90,75'")
	bam_attr=[]
	for ii,jj,mm,nn in zip(bamFiles,readLengths,Offsets,bamLegends):
		bam=bam_file_attr(ii,jj,mm,nn)
		bam_attr.append(bam)
	## calculate density for each bam files
	selectTrans,transLengthDict,startCodonCoorDict,stopCodonCoorDict,transID2geneID,transID2geneName,cdsLengthDict=reload_transcripts_information(options.coorFile)
	geneID2transID={v:k for k,v in transID2geneID.items()}
	geneName2transID={v:k for k,v in transID2geneName.items()}
	if options.in_selectTrans:
		select_trans=pd.read_csv(options.in_selectTrans,sep="\t")
		select_trans=set(select_trans.iloc[:,0].values)
		if options.id_type == 'transcript_id':
			select_trans=select_trans.intersection(selectTrans)
			print("There are " + str(len(select_trans)) + " transcripts from "+options.in_selectTrans+" used for following analysis.",file=sys.stderr)
		elif options.id_type == 'gene_id':
			tmp=[geneID2transID[gene_id] for gene_id in select_trans if gene_id in geneID2transID]
			select_trans=set(tmp)
			select_trans=select_trans.intersection(selectTrans)
			print("There are " + str(len(select_trans))+" gene id could be transformed into transcript id and used for following analysis.",file=sys.stderr)
		elif options.id_type == 'gene_name' or options.id_type=='gene_symbol':
			tmp=[geneName2transID[gene_name] for gene_name in select_trans if gene_name in geneName2transID]
			select_trans=set(tmp)
			select_trans=select_trans.intersection(selectTrans)
			print("There are " + str(len(select_trans))+" gene symbol could be transformed into transcript id and used for following analysis.",file=sys.stderr)
		else:
			raise IOError("Please input a approproate id_type parameters.[transcript_id/gene_id/gene_name/]")
	else:
		select_trans=selectTrans
	for bamfs in bam_attr:
		(bamfs.final_density_vector) = NormedDensityCalculation(bamfs.bamName,select_trans,transLengthDict,startCodonCoorDict,
        stopCodonCoorDict,options.min_cds_codon,options.min_cds_counts,options.norm_exclude_codon,options.min_norm_region_counts,bamfs.bamLen,bamfs.bamOffset,options.bins)
		print("Finish the step of read density calculation!",file=sys.stderr)
	## write density
	data=write_scaled_density_dataframe(bam_attr,options.output_prefix+"_scaled_density_dataframe.txt")
	print("Finish the step of MetageneAnalysisForTheWholeRegions!",file=sys.stderr)
	if options.plot.upper() in ['YES','Y']:
		MetagenePLotForTheWholeRegions(data,options.bins,options.output_prefix)
		print("Finish the step of plotting!",file=sys.stderr)
	elif options.plot.upper() in ['NO','N','NONE']:
		pass
	else:
		raise IOError("Please input a correct --plot parameter! [yes/no]")

if __name__=="__main__":
    main()

