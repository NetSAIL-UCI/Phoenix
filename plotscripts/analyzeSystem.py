import pandas as pd
import numpy as np

def processFinalOutput(df, folder, vals=None):
    if vals is None:
        vals = ["paths", "crit", "util"]
    
    var = "failure_level"
    cols = list(df.columns.values)
    
    for val in vals:
        required = []
        for header in cols:
            if val in header:
                required.append(header)
        print(required)
        s = df.groupby([var])[required].mean()
        if "path" in val or "util" in val:
            s = df.groupby([var])[required].mean()
            s = s * 100
            s = s[s.index.isin(levels)]
        elif "crit" in val:
            # required2 = required
            s = df.groupby('deployment_id')[required].apply(lambda x: (x) / (x.max()))
            s = s.reset_index()
            # print(s.head())
            # s.set_index(var)
            
            # print(s.head())
        #     # merge the original dataframe with the normalized column using the 'group' column as the key
            df = pd.merge(df, s, left_index=True, right_index=True)
            # print(list(df.columns.values))
            required2 = ["Phoenix_crit_y", 'Bestfit_Pri_crit_y', 'Bestfit_Fair_crit_y', 'LP_crit_y', 'failure_level']
            df = df[required2]
            # print(df.head())
            s = df
            s.set_index(var)
            # print(s.head())
            s = s[s['failure_level'].isin(levels)]
            # print(s)
            s = s.groupby([var])[required2[:-1]].mean()
            print(s)
            
        # print(s.values)
        with open(folder+val+".txt", "w") as f:
            f.write("failure Phoenix Bestfit_Pri Bestfit_Fair LP\n")
            f.write("\n".join(" ".join(map(str, x)) for x in (s.values)))
            # df_string = s.to_string(header=False, index=False)
            # f.write(df_string)
        f.close()
        
def processDf(df, val, levels, fname):    
    var = "failure_level"
    cols = list(df.columns.values)
    # print(cols)
    required = []
    for header in cols:
        if val in header:
            required.append(header)
    print(required)
    
    if "path" in val or "util" in val:
        s = df.groupby([var])[required].mean()
        print(s)
        # s = s * 100
        s = s[s.index.isin(levels)]
        print(s) 
    elif "resilience_score" in val or "util" in val:
        s = df.groupby([var])[required].mean()
        print(s)
        # s = s * 100
        s = s[s.index.isin(levels)]
        print(s)   
    elif "crit" in val or "revenue" in val:
        # required2 = required
        s = df.groupby('deployment_id')[required].apply(lambda x: (x) / (x.max()))
        s = s.reset_index()
        # print(s.head())
        # s.set_index(var)
        
        # print(s.head())
    #     # merge the original dataframe with the normalized column using the 'group' column as the key
        df = pd.merge(df, s, left_index=True, right_index=True)
        # print(list(df.columns.values))
        required2 = [ele+"_y" for ele in required]
        required2 = required2 + ['failure_level']
        # required2 = ["Phoenix_crit_y", 'Bestfit_Pri_crit_y', 'Bestfit_Fair_crit_y', 'LP_crit_y', 'failure_level']
        df = df[required2]
        # print(df.head())
        s = df
        s.set_index(var)
        # print(s.head())
        s = s[s['failure_level'].isin(levels)]
        # print(s)
        s = s.groupby([var])[required2[:-1]].mean()
        print(s)
    
    # print(s)
    # print(s)
    s = s.values
    print(s)
    # print(levels)
    # # # print(s)
    levels = np.array(levels).reshape(len(levels), 1)
    # print(levels)
    # print(s)
    s = np.hstack((levels,s))
    # print(s)
    with open(fname, "w") as f:
        # f.write("failure Phoenix Bestfit_Pri Bestfit_Fair LP\n")
        f.write("\n".join(" ".join(map(str, x)) for x in (s)))
        # df_string = s.to_string(header=False, index=False)
        # f.write(df_string)
    f.close()
        
def data_side_by_side(f1, f2, failure_levels=[0.1, 0.5, 0.9]):
    raw = "datasets/sosp_main/"
    f_1 = raw + f1
    df1 = pd.read_csv(f_1)
    f_2 = raw + f2
    df2 = pd.read_csv(f_2)
    vals = ["paths", "crit", "util"]
    outf = "processedData/"
    # val = "paths"
    for val in vals:
        fname1 = outf+"{}_{}.txt".format(f1.replace(".csv", ""), val)
        fname2 = outf+"{}_{}.txt".format(f2.replace(".csv", ""), val)
        # for val in vals:
        s1 = processDf(df1, val, failure_levels, fname1)
        s2 = processDf(df2, val, failure_levels, fname2)
    
    

def process_fig_7_data():
    alibaba = True
    raw = "asplos_25/"
    if alibaba:
        # f1 = "eval_osdi24_results_AlibabaOSDI-UniformServerLoad-Peak-CPMNoLimitPodResourceDist-FreqTaggingP90AtMost-100000.csv"
        f1 = "copied_code_eval_nsdi25_results_AlibabaOSDI-UniformServerLoad-Peak-CPMNoLimitPodResourceDist-GoogleTaggingP90-10000.csv"
        f_1 = raw + f1
        df = pd.read_csv(f_1)
    else:
        f2 = "Mix2UniformLongTail10000.csv"
        f_2 = raw + f2
        df = pd.read_csv(f_2)
    
    # data_side_by_side(f1, f2, failure_levels=[0.1, 0.5, 0.9])
   
    # print(df.head())
    outf = "asplos_25/processedData2/"
    print(df)
    failure_levels = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    vals = ["resilience_score", "crit", "revenue"]
    # vals = ["revenue"]
    for val in vals:
        if alibaba:
            fname1 = outf+"{}_{}.txt".format(f1.replace(".csv", ""), val)
            processDf(df, val, failure_levels, fname1)
        else:
            fname2 = outf+"{}_{}.txt".format(f2.replace(".csv", ""), val)
            processDf(df, val, failure_levels, fname2)
    