from airflow import DAG
from airflow.operators import BashOperator, PythonOperator
from datetime import datetime, timedelta
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy import or_, and_
import datetime
import os
import logging
from logging.config import dictConfig
from logging.handlers import RotatingFileHandler
from subprocess import call

logging_config = dict(
    version = 1,
    disable_existing_loggers = False,
    formatters = {
        'f': {'format':
              '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'}
        },
    handlers = {
        'h': {'class': 'logging.handlers.RotatingFileHandler',
              'formatter': 'f',
              'level': logging.DEBUG,
              'maxBytes': 100000000,
              'backupCount': 10,
              'filename': '/tmp/freebayes-regenotype-workflow.log'}
        },
    loggers = {
        'root': {'handlers': ['h'],
                 'level': logging.DEBUG}
        }
)

dictConfig(logging_config)
logger = logging.getLogger()

contig_names = ["1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19","20","21","22"]

reference_location = "/reference/genome.fa"
variants_location = "/shared/data/samples/vcf/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.snv.multibreak.vcf.gz"
variants_location = {
                     "1" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr1.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "2" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr2.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "3" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr3.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "4" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr4.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "5" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr5.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "6" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr6.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "7" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr7.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "8" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr8.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "9" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr9.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "10" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr10.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "11" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr11.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "12" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr12.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "13" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr13.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "14" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr14.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "15" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr15.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "16" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr16.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "17" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr17.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "18" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr18.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "19" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr19.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "20" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr20.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "21" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr21.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     "22" : "/shared/data/samples/vcf/1000GP_maf_0.01/ALL.chr22.wgs.phase3_shapeit2_mvncall_integrated_v5b.20130502.sites.af_0.01.vcf.gz", \
                     }
results_base_path = "/shared/data/results/regenotype"

def set_ready(my_run):
    if my_run.run_status == 1:
        print "Cannot put a run that's In Progress into a Ready status"
        
        logger.error("Attempting to put an In Progress run into Ready state, runID: %d", my_run.run_id)
        
        raise Exception()
    else:
        my_run.run_status = 0
        
def set_in_progress(my_run):
    if my_run.run_status != 0:
        
        logger.error("Wrong run status - %d, Only a Ready run can be put In Progress, runID: %d", my_run.run_status, my_run.run_id)
        raise Exception()
    else:
        my_run.run_status = 1
        my_run.run_start_date = datetime.datetime.now()
        
def set_finished(my_run):
    if my_run.run_status != 1:
        
        logger.error("Wrong run status - %d, Only an In Progress run can be Finished, runID: %d", my_run.run_status, my_run.run_id)
        raise Exception()
    else:
        my_run.run_status = 2
        my_run.run_end_date = datetime.datetime.now()
        
def set_error(my_run):
    my_run.run_status = 3

set_status = {"0": set_ready, "1": set_in_progress, "2": set_finished, "3": set_error}

def update_run_status(donor_index, sample_id, run_status):
    Base = automap_base()
    engine = create_engine('postgresql://pcawg_admin:pcawg@postgresql.service.consul:5432/germline_genotype_tracking')
    Base.prepare(engine, reflect=True)
    
    PCAWGSample = Base.classes.pcawg_samples
    SampleLocation = Base.classes.sample_locations
    GenotypingRun = Base.classes.genotyping_runs
    
    session = Session(engine)
    
    this_donor_index = donor_index
    this_sample_id = sample_id
    new_status = run_status
    
    my_run = session.query(GenotypingRun).filter(and_(GenotypingRun.donor_index==this_donor_index, GenotypingRun.sample_id==this_sample_id)).first()
    
    if not my_run:
        my_run = GenotypingRun()
        my_run.run_status = 0
        my_run.donor_index = this_donor_index
        my_run.sample_id = this_sample_id
        my_run.created_date = datetime.datetime.now()
        
        logger.info("No Genotyping Run found for donor %d. Creating new Genotyping Run", my_run.donor_index)
        
        session.add(my_run)
    
    set_status[new_status](my_run)
    my_run.last_updated_date = datetime.datetime.now()
    
    logger.info("Setting run status for donor %d to %d", my_run.donor_index, new_status)
    
    session.commit()
    session.close()
    engine.dispose()

def get_next_sample():    
    Base = automap_base()
    engine = create_engine('postgresql://pcawg_admin:pcawg@postgresql.service.consul:5432/germline_genotype_tracking')
    Base.prepare(engine, reflect=True)
    
    PCAWGSample = Base.classes.pcawg_samples
    SampleLocation = Base.classes.sample_locations
    GenotypingRun = Base.classes.genotyping_runs
    
    session = Session(engine)
    
    
    logger.debug("Getting next available sample")
    
    next_sample = session.query(PCAWGSample.index, PCAWGSample.normal_wgs_alignment_gnos_id, SampleLocation.normal_sample_location, GenotypingRun.run_id).\
        join(SampleLocation, PCAWGSample.index == SampleLocation.donor_index).\
        outerjoin(GenotypingRun,PCAWGSample.index == GenotypingRun.donor_index).\
        filter(\
               and_(SampleLocation.normal_sample_location != None, \
                    or_(GenotypingRun.run_status == None, and_(GenotypingRun.run_status != 1, GenotypingRun.run_status != 2))\
        )).\
        first()
    
    my_run_id = next_sample.run_id    
    donor_index = next_sample.index
    sample_id = next_sample.normal_wgs_alignment_gnos_id
    sample_location = next_sample.normal_sample_location
    
    logger.info("Got the next available sample Donor Index: %d, Sample ID: %s, Sample Location: %s, Genotyping Run: %d.", donor_index, sample_id, sample_location, my_run_id)
    
    
    my_run = None
    
    if not my_run_id:
        my_run = GenotypingRun()
        my_run.run_status = 0
        my_run.donor_index = donor_index
        my_run.sample_id = sample_id
        my_run.created_date = datetime.datetime.now()
        
        logger.info("No Genotyping Run found for donor %d. Creating new Genotyping Run", my_run.donor_index)
        
        
        session.add(my_run)
    else:
        my_run = session.query(GenotypingRun).get(my_run_id)
    
    set_status["1"](my_run)
    my_run.last_updated_date = datetime.datetime.now()
    
    logger.info("Setting run status for donor %d to In Progress", my_run.donor_index)
    
    session.commit()
    session.close()
    engine.dispose()

    if next_sample != None:
        return (donor_index, sample_id, sample_location)
    else:
        logger.error("Could not find the next sample")
        raise Exception()
    

def reserve_sample():
    return get_next_sample()
    

def set_error():
   logger.info("Setting error state for run.")
   os.system("/tmp/germline-regenotyper/scripts/update-sample-status.py {{ task_instance.xcom_pull(task_ids='reserve_sample')[0] }} {{ task_instance.xcom_pull(task_ids='reserve_sample')[1] }} 3")         

def run_freebayes(**kwargs):
    contig_name = kwargs["contig_name"]
    ti = kwargs["ti"]
    
    donor_index = ti.xcom_pull(task_ids='reserve_sample')[0]
    sample_id = ti.xcom_pull(task_ids='reserve_sample')[1]
    sample_location = ti.xcom_pull(task_ids='reserve_sample')[2]
    logger.info("Got sample assignment from the sample reservation task: %d %s %s", donor_index, sample_id, sample_location)
    
    
    result_path_prefix = "/tmp/freebayes-regenotype/" + sample_id
    
    if (not os.path.isdir(result_path_prefix)):
        logger.info("Results directory %s not present, creating.", result_path_prefix)
        os.makedirs(result_path_prefix)
    
    result_filename = result_path_prefix + "/" + sample_id + "_regenotype_" + contig_name + ".vcf"
    
    
    freebayes_command = "/bin/freebayes -r " + contig_name +\
                        " -f " + reference_location +\
                        " -@ " + variants_location[contig_name] +\
                        " -l " + sample_location +\
                        " > " + result_filename
    
    logger.info("About to invoke freebayes with command %s.", freebayes_command)
    #os.system(freebayes_command)
    try:
        retcode = call(freebayes_command, shell=True)
        if retcode != 0:
            logger.error("Freebayes terminated by signal %d.", retcode)
            raise Exception("Freebayes terminated by signal" + str(retcode))
        else:
            logger.info("Freebayes terminated normally.")
    except OSError as e:
        logger.error("Freebayes execution failed %s.", e)
        raise
        
    generate_tabix(compress_sample(result_filename))
    copy_result(donor_index, sample_id, contig_name)

def compress_sample(result_filename):
    compressed_filename = result_filename + ".gz"
    compression_command = "/usr/local/bin/bgzip " + result_filename
    
    logger.info("About to compress sample %s. Using command: %s.", result_filename, compression_command)
    #os.system(compression_command)
    try:
        retcode = call(compression_command, shell=True)
        if retcode != 0:
            logger.error("Compression terminated by signal %d.", retcode)
            raise Exception("Compression terminated by signal" + str(retcode))
        else:
            logger.info("Compression terminated normally.")
    except OSError as e:
        logger.error("Compression failed %s.", e)
        raise
    
    
    return compressed_filename
      
def generate_tabix(compressed_filename):
    tabix_command = "/usr/local/bin/tabix -f -p vcf " + compressed_filename
    
    logger.info("About to generate tabix for %s. Using command: %s.", compressed_filename, tabix_command)
    
    #os.system(tabix_command)
    try:
        retcode = call(tabix_command, shell=True)
        if retcode != 0:
            logger.error("Tabix generation terminated by signal %d.", retcode)
            raise Exception("Tabix generation terminated by signal" + str(retcode))
        else:
            logger.info("Tabix generation terminated normally.")
    except OSError as e:
        logger.error("Tabix generation failed %s.", e)
        raise
    
    
         
    
def copy_result(donor_index, sample_id, contig_name): 
    results_directory_command = "mkdir -p " + results_base_path + "/" + sample_id
    #os.system(results_directory_command)
    try:
        retcode = call(results_directory_command, shell=True)
        if retcode != 0:
            logger.error("Results directory creation terminated by signal %d.", retcode)
            raise Exception("Results directory creation terminated by signal" + str(retcode))
    except OSError as e:
        logger.error("Results directory creation failed %s.", e)
        raise
    
    move_command = "rsync -a -v --remove-source-files /tmp/freebayes-regenotype/" + sample_id + "/" + sample_id + "_regenotype_" + contig_name + ".vcf.gz* " + results_base_path + "/" + sample_id + "/"
    logger.info("About to move results for %d %s to shared storage. Using command '%s'", donor_index, sample_id, move_command)
    
    #os.system(copy_command)
    try:
        retcode = call(move_command, shell=True)
        if retcode != 0:
            logger.error("Results moving terminated by signal %d.", retcode)
            raise Exception("Results moving terminated by signal" + str(retcode))
        else:
            logger.info("Results moving terminated normally.")
    except OSError as e:
        logger.error("Results moving failed %s.", e)
        raise
     
        
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime.datetime(2020,01,01),
    'email': ['airflow@airflow.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG("freebayes-regenotype", default_args=default_args,schedule_interval=None,concurrency=10000,max_active_runs=2000)


reserve_sample_task = PythonOperator(
    task_id = "reserve_sample",
    python_callable = reserve_sample,
    priority_weight = 10,
    dag = dag)

release_sample_task = BashOperator(
    task_id = "release_sample",
    bash_command = "python /tmp/germline-regenotyper/scripts/update-sample-status.py {{ task_instance.xcom_pull(task_ids='reserve_sample')[0] }} {{ task_instance.xcom_pull(task_ids='reserve_sample')[1] }} 2",
    priority_weight = 50,
    dag = dag)

for contig_name in contig_names:
    genotyping_task = PythonOperator(
       task_id = "regenotype_" + contig_name,
       python_callable = run_freebayes,
       op_kwargs={"contig_name": contig_name},
       provide_context=True,
       priority_weight = 20,
       dag = dag)
    
    genotyping_task.set_upstream(reserve_sample_task)
    
    release_sample_task.set_upstream(genotyping_task)