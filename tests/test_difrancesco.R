# Di Francesco et al.'s dietary restriction (dr/difrancesco.R): each refusal of the table (its columns, its 937 mice,
# a repeated MouseID, the diets' levels and counts, the 13 censored, the lifespans); the Kaplan-Meier median and the
# log-rank statistic written here, and survival's, on known answers; the verdict at and beside each of its seven
# conditions; the JSON writer; the seed refused; and, with the deposit at inputs/ (or DR_INPUTS), that it is the
# pinned file and its table is as the paper states, which computes no lifespan statistic.
#
# Run with: Rscript tests/test_difrancesco.R

args <- commandArgs(FALSE)
here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", args, value = TRUE)[1])))
source(file.path(here, "..", "dr", "difrancesco.R"))

failures <- 0L
check <- function(name, ok) {
  ok <- isTRUE(tryCatch(ok, error = function(e) FALSE))
  cat(if (ok) "ok  " else "FAIL", name, "\n")
  if (!ok) failures <<- failures + 1L
}
refused <- function(expr) inherits(tryCatch({ force(expr); NULL }, refused = function(e) e), "refused")

fake <- function() {
  diet <- factor(rep(DIETS, COUNTS), levels = DIETS)
  n <- length(diet)
  died <- rep(TRUE, n)
  died[seq_len(CENSORED)] <- FALSE
  data.frame(MouseID = sprintf("DO-%04d", seq_len(n)), Diet = diet, SurvDays = 400 + seq_len(n), Died = died,
             stringsAsFactors = FALSE)
}

# The table
good <- check_table(fake())
check("a good table is read, in months", nrow(good) == 937 && abs(good$SurvMonths[1] - 401 / 30.4) < 1e-12)
bad <- list(
  "a missing column" = fake()[, c("MouseID", "Diet", "SurvDays")],
  "936 mice" = fake()[-1, ],
  "a repeated MouseID" = within(fake(), MouseID[2] <- MouseID[1]),
  "other levels" = within(fake(), Diet <- factor(as.character(Diet), levels = c("AL", "1D", "2D", "20", "40", "X"))),
  "a mouse moved between diets" = within(fake(), Diet[1] <- "1D"),
  "a missing Died" = within(fake(), Died[100] <- NA),
  "12 censored" = within(fake(), Died[1] <- TRUE),
  "a zero lifespan" = within(fake(), SurvDays[5] <- 0),
  "a lifespan as text" = within(fake(), SurvDays <- as.character(SurvDays)))
for (k in names(bad)) check(paste("refuses", k), refused(check_table(bad[[k]])))

# Known answers
check("own median 2.5 where S sits at 0.5 from 2 to 3", abs(km_median_own(c(1, 2, 3, 4), rep(TRUE, 4)) - 2.5) < 1e-12)
check("own median 4 with a censored time", abs(km_median_own(c(1, 2, 3, 4, 5), c(TRUE, FALSE, TRUE, TRUE, TRUE)) - 4) < 1e-12)
check("own log-rank 8/13", abs(logrank_own(c(1, 3, 2, 4), rep(TRUE, 4), factor(c("A", "A", "B", "B"))) - 8 / 13) < 1e-12)
check("the known answers hold for both implementations", known_answers())
check("own log-rank agrees with survdiff on a three-group table with ties and censoring", {
  set.seed(1)
  tt <- round(rexp(90, 1 / 20)) + 1
  ee <- runif(90) > 0.2
  gg <- factor(rep(c("x", "y", "z"), 30))
  abs(logrank_own(tt, ee, gg) - survdiff(Surv(tt, ee) ~ gg)$chisq) < 1e-9
})
check("own medians agree with survfit on the fake table", {
  m <- km_medians(good)
  own <- vapply(DIETS, function(k) km_median_own(good$SurvMonths[good$Diet == k], good$Died[good$Diet == k]), 0)
  all(abs(m - own) < 1e-9)
})

# The verdict
med <- c(AL = 100, `1D` = 105.9, `2D` = 105.3, `20` = 109.1, `40` = 118.2)
check("all seven at the registered gains", all(conditions(med, 0.0099)) && length(conditions(med, 0.0099)) == 7)
check("p of 0.01 fails one", sum(conditions(med, 0.01)) == 6)
for (k in c("1D", "2D", "20", "40")) {
  m2 <- med
  m2[[k]] <- m2[[k]] - 0.02
  check(paste("just short of the", k, "gain fails it"), sum(conditions(m2, 0.001)) <= 6)
}
check("20% below a fasting group fails one", sum(conditions(c(AL = 100, `1D` = 110, `2D` = 106, `20` = 109.5, `40` = 120), 0.001)) == 6)
check("40% not above 20% fails one", sum(conditions(c(AL = 100, `1D` = 106, `2D` = 106, `20` = 120, `40` = 119), 0.001)) == 6)

# The JSON writer
check("strings are escaped", json_value('a "b" \\ c') == '"a \\"b\\" \\\\ c"')
check("numbers and logicals", json_value(1.25e-23) == "1.25e-23" && json_value(7L) == "7" && json_value(TRUE) == "true")
check("a named list is an object", json_value(list(a = 1, b = "x")) == '{"a": 1, "b": "x"}')

# The seed
check("a bad seed is refused", refused(run("xyz", inputs = tempfile(), results = tempfile())))

# The pinned deposit, if present: its structure only
inputs <- Sys.getenv("DR_INPUTS", file.path(here, "..", "inputs"))
if (file.exists(file.path(inputs, INPUT$name))) {
  d <- read_table(inputs)
  check("the pinned deposit's table is as the paper states", nrow(d) == 937 && sum(!d$Died) == 13)
} else cat("skip the pinned deposit (not at", inputs, ")\n")

cat(failures, "failures\n")
quit(status = if (failures > 0L) 1L else 0L)
