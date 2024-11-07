import org.apache.spark.sql.types._
import org.apache.spark.graphx._
import org.apache.spark.sql.Row


val df1 = spark.read.format("csv").option("header", "true").load("/scratch/kapila1/spark_dump/nsdi24/alibaba_2021_microservice_traces_7days_preprocessed.csv").select("traceid","um","dm","rpcid")
val df1_filter = df1.dropDuplicates()

val customSchema=StructType(Array(StructField("interface", StringType, nullable=true),StructField("traceid", StringType, nullable=true)))

val svc_traceid = spark.read.format("csv").schema(customSchema).load("/scratch/kapila1/spark_dump/asplos25/svc_traceid_map")

for (i <- 0 to 18) {

val filename = "/scratch/kapila1/spark_dump/asplos25/app_services_map/" + i.toString + ".csv" // Using toString method
val customSchema=StructType(Array(StructField("interface", StringType, nullable=true)))

val df2 = spark.read.format("csv").option("header", "false").schema(customSchema).load(filename)

val df2_filter = df2.dropDuplicates()

val joinedDf = svc_traceid.join(df2_filter, Seq("interface"), "inner")

val svc_counts = joinedDf.groupBy("interface").count()

val joined2 = df1_filter.join(joinedDf, Seq("traceid"), "inner")

val groupDf = joined2.withColumn("um-dm", concat(col("um"), lit("-"), col("dm")))

val groupedDf = groupDf.groupBy("interface").agg(collect_set("um-dm").as("graph"))

val stringDF = groupedDf.withColumn("graph_str", concat_ws(",", $"graph")).select("interface", "graph_str")

val countAdded = stringDF.join(svc_counts, Seq("interface"), "left")
val outfile = "/scratch/kapila1/spark_dump/asplos25/app_servicegraphs/" + i.toString  // Using toString method
countAdded.repartition(1).write.csv(outfile)
}
