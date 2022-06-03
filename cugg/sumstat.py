# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/01_Sumstat.ipynb (unless otherwise specified).

__all__ = ['p2z', 'Sumstat', 'ss_2_vcf']

# Cell
import yaml
import numpy as np
import pandas as pd
from scipy.stats import norm
from .utils import *

# Cell
def p2z(pval,beta,twoside=True):
    if twoside:
        pval = pval/2
    z=np.abs(norm.ppf(pval))
    ind=beta<0
    z[ind]=-z[ind]
    return z

class Sumstat:
    def __init__(self,sumstat_path,config_file=None,rename=True):
        self.ss = self.read_sumstat(sumstat_path,config_file,rename)

    def __repr__(self):
        return "sumstat:% s" % (self.ss)

        #functions to read sumstats
    def read_sumstat(self,file, config_file,rename):
        if config_file is not None:
            config_file = yaml.safe_load(open(config_file, 'r'))
        return read_sumstat(file,config_file,rename)

    def extractbyregion(self,region):
        sumstats = self.ss
        idx = (sumstats.CHR == region[0]) & (sumstats.POS >= region[1]) & (sumstats.POS <= region[2])
        print('this region',region,'has',sum(idx),'SNPs in Sumstat')
        self.ss = sumstats[idx]

    def extractbyvariants(self,variants,notin=False):
        idx = self.ss.SNP.isin(variants)
        if notin:
            idx = idx == False
        #update sumstats
        self.ss = self.ss[idx]

    def calculateZ(self):
        self.ss['Z'] = list(p2z(self.ss.P,self.ss.BETA))

    def match_ss(self,bim):
        self.ss = check_ss1(self.ss,bim)



# Cell
    def read_sumstat(file, config,rename=True):
        try:
            sumstats = pd.read_csv(file, compression='gzip', header=0, sep='\t', quotechar='"')
        except:
            sumstats = pd.read_csv(file, header=0, sep='\t', quotechar='"')
        if config is not None:
            try:
                ID = config.pop('ID').split(',')
                sumstats = sumstats.loc[:,list(config.values())]
                sumstats.columns = list(config.keys())
                sumstats.index = namebyordA0_A1(sumstats[ID],cols=ID)
            except:
                raise ValueError(f'According to config_file, input summary statistics should have the following columns: %s' % list(config.values()))
            sumstats.columns = list(config.keys())
        if rename:
            sumstats.SNP = 'chr'+sumstats.CHR.astype(str).str.strip("chr") + ':' + sumstats.POS.astype(str) + '_' + sumstats.A0.astype(str) + '_' + sumstats.A1.astype(str)
        sumstats.CHR = sumstats.CHR.astype(str).str.strip("chr").astype(int)
        sumstats.POS = sumstats.POS.astype(int)
        if "GENE" in sumstats.columns.values():
            sumstats.index = namebyordA0_A1(sumstats[["GENE","CHR","POS","A0","A1"]],cols=["GENE","CHR","POS","A0","A1"])
        else:
            sumstats.index = namebyordA0_A1(sumstats[["CHR","POS","A0","A1"]],cols=["CHR","POS","A0","A1"])
        return sumstats

# Cell
def ss_2_vcf(ss_df,name = "name"):
    ## Geno field
    df = pd.DataFrame()
    df[['#CHROM', 'POS', 'ID', 'REF', 'ALT']] = ss_df[['CHR', 'POS', 'SNP', 'A0', 'A1']].sort_values(['CHR', 'POS'])
    ## Info field(Empty)
    df['QUAL'] = "."
    df['FILTER'] = "PASS"
    df['INFO'] = "."
    fix_header = ["SNP","A1","A0","POS","CHR","STAT","SE","P"]
    header_list = []
    if "GENE" in ss_df.columns:
        df['INFO'] = "GENE = " + ss_df["GENE"]
        fix_header = ["GENE","SNP","A1","A0","POS","CHR","STAT","SE","P"]
        header_list = ['##INFO=<ID=GENE,Number=A,Type=String,Description="The name of genes']
    ### Fix headers
    import time
    header = '##fileformat=VCFv4.2\n' + \
    '##FILTER=<ID=PASS,Description="All filters passed">\n' + \
    f'##fileDate={time.strftime("%Y%m%d",time.localtime())}\n'+ \
    '##FORMAT=<ID=ES,Number=A,Type=Float,Description="Effect size estimate relative to the alternative allele">\n' + \
    '##FORMAT=<ID=SE,Number=A,Type=Float,Description="Standard error of effect size estimate">\n' + \
    '##FORMAT=<ID=P,Number=A,Type=Float,Description="The Pvalue corresponding to ES">\n'
    ### Customized Field headers
    for x in ss_df.columns:
        if x not in fix_header:
            Prefix = f'##FORMAT=<ID={x},Number=A,Type='
            Type = str(type(test[x][0])).replace("<class \'","").replace("'>","").replace("numpy.","").replace("64","").capitalize()
            Surfix = f',Description="Customized Field {x}'
            header_list.append(Prefix+Type+Surfix)
    ## format and sample field
    df['FORMAT'] = ":".join(["STAT","SE","P"] + ss_df.drop(fix_header,axis = 1).columns.values.tolist())
    df[f'{name}'] = ss_df['STAT'].astype(str) + ":" + ss_df['SE'].astype(str) + ":" + ss_df['P'].astype(str) + ss_df.drop(fix_header,axis = 1).astype(str).apply(":".join,axis = 1)
    ## Rearrangment
    df = df[['#CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'FILTER', 'INFO','FORMAT',f'{name}']]
    # Add headers
    header = header + "\n".join(header_list)
    return df,header