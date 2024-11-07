
import org.apache.spark.sql.functions._
import org.apache.spark.sql.DataFrame
import org.apache.spark.sql.{SparkSession, functions}

val df = spark.read.format("csv").option("header", "true").load("/scratch/kapila1/spark_dump/nsdi24/alibaba_2021_microservice_traces_7days_preprocessed.csv").dropDuplicates()
val dfs = df.filter(col("rpcid") ==="0") 
val svc = dfs.select("interface") // At rpcid = 0, the interface means the service, at other rpcs this could be different.
val usvc = svc.distinct() // getting unique service_ids
val dfsvc = dfs.join(usvc, Seq("interface"), "inner") 
val utraceids = dfsvc.select("interface", "traceid")
utraceids.distinct().repartition(1).write.csv("/scratch/kapila1/spark_dump/asplos25/svc_traceid_map") // This represents which trace_ids belong to which service_ids
val edges = df.filter(col("rpcid") =!= "0").select("traceid", "um", "dm") // when rpcid is non-zero that means this are edges in a graph
val vert = edges.selectExpr("um as ID", "traceid").union(edges.selectExpr("dm as ID","traceid")) // just fetching all the different vertices in the graph 
val vertWithserv = vert.join(utraceids,Seq("traceid"),"inner")
val serv_nodes = vertWithserv.groupBy("interface").agg(collect_set("id").as("nodes")).filter(col("interface") =!= "") //Filtering because a null interface gets a lot of traces
val serv_nodes_count = serv_nodes.withColumn("count", functions.size(col("nodes")))
val matrix = serv_nodes_count.crossJoin(serv_nodes_count.withColumnRenamed("nodes", "right_nodes").withColumnRenamed("interface", "right_interface").withColumnRenamed("count","right_count"))
val matrixWintersection = matrix.withColumn("intersection", functions.array_intersect(col("nodes"), col("right_nodes")))
val matrixWintersection_count = matrixWintersection.withColumn("int_count", functions.size(col("intersection")))
val isConnected = matrixWintersection_count.withColumn("connected", functions.when((col("int_count") > functions.expr("0.2 * count") && col("int_count") > functions.expr("0.2 * right_count")), 1).otherwise(0))
val final_mat = isConnected.select("interface","right_interface","connected")
final_mat.repartition(1).write.csv("/scratch/kapila1/spark_dump/asplos25/matrix")