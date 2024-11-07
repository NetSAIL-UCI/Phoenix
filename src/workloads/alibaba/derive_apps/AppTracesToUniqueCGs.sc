import org.apache.spark.sql.types._
import org.apache.spark.graphx._
import org.apache.spark.sql.Row

val customSchema=StructType(Array(StructField("traceid", StringType, nullable=true)))

val df1 = spark.read.format("csv").option("header", "true").load("/scratch/kapila1/spark_dump/nsdi24/alibaba_2021_microservice_traces_7days_preprocessed.csv").select("traceid","um","dm","rpcid")

val df1_filter = df1.dropDuplicates()

for (i <- 0 to 18) {

val filename = "/scratch/kapila1/spark_dump/asplos25/app_traceids_map/" + i.toString + ".csv" // Using toString method

val df2 = spark.read.format("csv").option("header", "false").schema(customSchema).load(filename)

val df2_filter = df2.dropDuplicates()

val joinedDf = df1_filter.join(df2_filter, Seq("traceid"), "inner")

// val filteredDf = joinedDf.select("traceid", "um", "dm")

val groupDf = joinedDf.withColumn("um-dm", concat(col("um"), lit("-"), col("dm")))

val groupedDf = groupDf.groupBy("traceid").agg(collect_set("um-dm").as("graph"))

val sortedDF = groupedDf.withColumn("sgraph", sort_array($"graph"))

val simGraphs = sortedDF.groupBy("sgraph").count()

val stringDF = simGraphs.withColumn("graph_str", concat_ws(",", $"sgraph")).select("graph_str","count")

val outfile = "/scratch/kapila1/spark_dump/asplos25/app_callgraphs/" + i.toString  // Using toString method
stringDF.repartition(1).write.csv(outfile)
}
