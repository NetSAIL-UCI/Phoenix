// import org.apache.spark.sql.types._
// import org.apache.spark.sql.functions._


// val df1 = spark.read.format("csv").option("header", "true").load("/scratch/kapila1/spark_dump/nsdi24/alibaba_2021_microservice_traces_7days_preprocessed.csv").select("traceid","um","dm","rpcid","rt", "timestamp").dropDuplicates()

// val convertedDF = df1.withColumn("rt_n", col("rt").cast("double")).withColumn("absrt", abs(col("rt_n"))).groupBy("dm").agg(expr("percentile(absrt, 0.5)").alias("50thPercentile"), expr("percentile(absrt, 0.9)").alias("90thPercentile"))

// val entry = convertedDF.filter(col("dm")==="7695b43b41732a0f15d3799c8eed2852665fe8da29fd700c383550fc16e521a3")

// val df = df1.withColumn("ts", to_timestamp(col("timestamp")/1000))

// val df2 = df.withColumn("minute",minute(col("ts")))

// val df3 = df2.groupBy("dm", "minute").count()

// val df4 = df3.groupBy("dm").agg(expr("percentile(count, 0.5)").alias("P50"), expr("percentile(count, 0.9)").alias("P90"), max("count"))

// val outfile = "/scratch/kapila1/spark_dump/nsdi24/freq_per_dm/" 
// df4.repartition(1).write.csv(outfile)

import org.apache.spark.sql.types._
import org.apache.spark.graphx._
import org.apache.spark.sql.Row

val customSchema=StructType(Array(StructField("traceid", StringType, nullable=true)))

val df1 = spark.read.format("csv").option("header", "true").load("/scratch/kapila1/spark_dump/nsdi24/alibaba_2021_microservice_traces_7days_preprocessed.csv").select("traceid","um","dm","rpcid", "timestamp")

val df1_filter = df1.dropDuplicates()

for (i <- 0 to 18) {

val filename = "/scratch/kapila1/spark_dump/asplos25/app_traceids_map/" + i.toString + ".csv" // Using toString method

val df2 = spark.read.format("csv").option("header", "false").schema(customSchema).load(filename)

val df2_filter = df2.dropDuplicates()

val joinedDf = df1_filter.join(df2_filter, Seq("traceid"), "inner")

val df = joinedDf.withColumn("ts", to_timestamp(col("timestamp")/1000))

val df3 = df.withColumn("minute",minute(col("ts")))

val df4 = df3.groupBy("dm", "minute").count()

val df5 = df4.groupBy("dm").agg(expr("percentile(count, 0.5)").alias("P50"), expr("percentile(count, 0.9)").alias("P90"), max("count"))

val outfile = "/scratch/kapila1/spark_dump/asplos25/cpm_per_dm_per_app/" + i.toString
df5.repartition(1).write.csv(outfile)

}
