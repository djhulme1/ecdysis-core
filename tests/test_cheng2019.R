# Cheng et al.'s female survival advantage (itp/cheng2019.R): the worksheet reader on XML written here (inline
# strings, shared strings, numbers, absent cells, and every refusal); rule 1's checks and refusals on made-up rows; the
# peak, the steps and the three conditions on made-up ratio curves; the bootstrap's indices; the JSON writer; the seed
# refused. With bshazard's six files at inputs/ (or CHENG_INPUTS): its fits on simulated mice only (the binning's
# totals, bshazard() against the module's call of bspois, the same mice for both sexes, the planted peaks). With the
# workbooks there too: that each is the pinned file and holds its rows and controls as pinned, which computes nothing
# from an age.
#
# Run with: Rscript tests/test_cheng2019.R

args <- commandArgs(FALSE)
here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", args, value = TRUE)[1])))
source(file.path(here, "..", "itp", "cheng2019.R"))

failures <- 0L
check <- function(name, ok) {
  ok <- isTRUE(tryCatch(ok, error = function(e) FALSE))
  cat(if (ok) "ok  " else "FAIL", name, "\n")
  if (!ok) failures <<- failures + 1L
}
refused <- function(expr) inherits(tryCatch({ force(expr); NULL }, refused = function(e) e), "refused")

# ---------------------------------------------------------------- the worksheet reader

inline <- function(ref, text) sprintf('<c r="%s" t="inlineStr"><is><t>%s</t></is></c>', ref, text)
num <- function(ref, x) sprintf('<c r="%s"><v>%s</v></c>', ref, x)
shr <- function(ref, k) sprintf('<c r="%s" s="1" t="s"><v>%d</v></c>', ref, k)
sheet <- function(rows) paste0('<worksheet><sheetData>',
                               paste0('<row r="', seq_along(rows), '">', rows, '</row>', collapse = ""),
                               '</sheetData></worksheet>')

m <- sheet_cells(sheet(c(paste0(inline("A1", "a"), inline("B1", "b"), inline("C1", "c")),
                         paste0(inline("A2", "x &amp; y"), num("C2", "887")))), character(0))
check("inline strings and numbers, an absent cell NA", identical(dim(m), c(2L, 3L)) && m[2, "A"] == "x & y" &&
        is.na(m[2, "B"]) && m[2, "C"] == "887")
sh <- shared_strings('<sst><si><t>population</t></si><si><r><t>co</t></r><r><t>hort</t></r></si><si><t>m</t><rPh><t>X</t></rPh></si></sst>')
check("shared strings: runs joined, phonetic runs left out", identical(sh, c("population", "cohort", "m")))
m2 <- sheet_cells(sheet(c(paste0(shr("A1", 0), shr("B1", 1)), paste0(shr("A2", 2), num("B2", "1")))), sh)
check("shared-string cells read through the table", m2[1, "A"] == "population" && m2[1, "B"] == "cohort" &&
        m2[2, "A"] == "m" && m2[2, "B"] == "1")
check("a self-closing cell is NA", is.na(sheet_cells(sheet(c(paste0(num("A1", "1"), '<c r="B1" s="2"/>'))),
                                                     character(0))[1, "B"]))
check("a newline inside a cell's text is kept", sheet_cells(sheet(inline("A1", "two\nlines")), character(0))[1, "A"] ==
        "two\nlines")
check("columns past Z order after Z", identical(colnames(sheet_cells(sheet(paste0(num("AA1", 1), num("B1", 2),
                                                                           num("Z1", 3))), character(0))),
                                               c("B", "Z", "AA")))
check("refuses a shared string out of range", refused(sheet_cells(sheet(shr("A1", 3)), sh)))
check("refuses a boolean or formula cell", refused(sheet_cells(sheet('<c r="A1" t="b"><v>1</v></c>'), character(0))) &&
        refused(sheet_cells(sheet('<c r="A1" t="str"><f>1+1</f><v>2</v></c>'), character(0))))
check("refuses a sheet with no cells", refused(sheet_cells("<worksheet><sheetData/></worksheet>", character(0))))
check("refuses a cell given twice", refused(sheet_cells(sheet(paste0(num("A1", 1), num("A1", 2))), character(0))))

# ---------------------------------------------------------------- rule 1

fake_cohort <- function(cohort = "C2010") {
  n <- ROWS[[cohort]]
  k <- CONTROLS[[cohort]]
  groups <- setdiff(GROUPS[[cohort]], "Control")
  ctl <- c(rep("m", k[["m"]]), rep("f", k[["f"]]))
  rest <- n - length(ctl)
  d <- data.frame(population = POPULATION, cohort = cohort, site = rep(SITES, length.out = n),
                  sex = c(ctl, rep(c("m", "f"), length.out = rest)), id = sprintf("X%05d", seq_len(n)),
                  group = c(rep("Control", length(ctl)), rep(groups, length.out = rest)),
                  dose = c(rep("0", length(ctl)), rep("100", rest)),
                  age_initiation = c(rep(NA, length(ctl)), rep("4", rest)),
                  status = "dead", dead = "1", age = as.character(300 + seq_len(n) %% 900),
                  stringsAsFactors = FALSE)
  d$status[5] <- "removed"
  d$dead[5] <- "0"
  d
}
good <- controls_of(fake_cohort(), "C2010")
check("a good cohort gives its controls, a removal censored", nrow(good) == 580 && sum(good$sex == "m") == 300 &&
        good$dead[5] == 0L && all(good$dead[-5] == 1L) && is.numeric(good$age))
check("an age written 887.0 is read as 887", {
  d <- fake_cohort(); d$age[1] <- "887.0"; controls_of(d, "C2010")$age[1] == 887 })
bad <- list(
  "a row too few" = fake_cohort()[-1700, ],
  "another population" = within(fake_cohort(), population[3] <- "B6"),
  "another cohort" = within(fake_cohort(), cohort[3] <- "C2009"),
  "another site" = within(fake_cohort(), site[3] <- "NIA"),
  "another sex" = within(fake_cohort(), sex[700] <- "u"),
  "an age with a fraction" = within(fake_cohort(), age[3] <- "887.5"),
  "a missing age" = within(fake_cohort(), age[3] <- NA),
  "status and dead disagreeing" = within(fake_cohort(), dead[4] <- "0"),
  "an unknown status" = within(fake_cohort(), status[4] <- "alive"),
  "an unknown group" = within(fake_cohort(), group[1000] <- "Met"),
  "a group missing" = within(fake_cohort(), group[group == "ND_mid"] <- "ND_lo"),
  "a control with a dose" = within(fake_cohort(), dose[2] <- "14"),
  "a control with a starting age" = within(fake_cohort(), age_initiation[2] <- "9"),
  "a control moved to a treated group" = within(fake_cohort(), group[2] <- "FO_hi"))
for (k in names(bad)) check(paste("refuses", k), refused(controls_of(bad[[k]], "C2010")))

# ---------------------------------------------------------------- the peak, the steps, the conditions

curve <- function(peak_at, h = 2.2) 1 + (h - 1) * exp(-((GRID - peak_at) / 150)^2)
r <- curve(350)
p <- peak_of(r)
st <- steps_of(r, p$age)
check("the peak of a made-up curve", p$age == 350 && abs(p$ratio - 2.2) < 1e-12)
check("its steps: 350, 450, ..., 750", identical(as.integer(st$ages), c(350L, 450L, 550L, 650L, 750L)))
check("all three conditions on it", all(conditions(p, 1.5, st)))
check("a peak at 460 days fails the first", {
  q <- peak_of(curve(460)); c_ <- conditions(q, 1.5, steps_of(curve(460), q$age)); !c_[[1]] && c_[[2]] && c_[[3]] })
check("a lower limit of 1 fails the second", !conditions(p, 1, st)[[2]])
check("a ratio of 1 at the peak fails the second", { q <- p; q$ratio <- 1; !conditions(q, 1.2, st)[[2]] })
check("a rise at 650 days fails the third", {
  r2 <- r; r2[GRID >= 640 & GRID <= 660] <- r2[match(550, GRID)] + 0.01
  !conditions(p, 1.5, steps_of(r2, p$age))[[3]] })
check("a peak past 700 days has no step and fails the third", {
  q <- peak_of(curve(760)); s <- steps_of(curve(760), q$age); length(s$ages) == 1 && !conditions(q, 1.5, s)[[3]] })
check("a peak past 800 days is handled", { q <- peak_of(curve(900)); length(steps_of(curve(900), q$age)$ages) == 1 })
check("ties go to the first age", peak_of(c(1, 3, 3, 2), 1:4)$age == 2L)
check("an all-NA curve has no peak", is.na(peak_of(rep(NA_real_, 4), 1:4)$age))
check("the limits are type 7 quantiles, ignoring NA", {
  R <- cbind(c(1:9, NA), 1:10)
  l <- limits(R)
  abs(l$lower[2] - quantile(1:10, 0.025, type = 7)) < 1e-12 && abs(l$lower[1] - quantile(1:9, 0.025, type = 7)) < 1e-12 &&
    identical(l$n, c(9, 10))
})

# ---------------------------------------------------------------- the bootstrap's indices, the seed, the writer

s1 <- strrep("3c", 32)
i1 <- draw_indices(s1, 50, 40)
i2 <- draw_indices(s1, 50, 40)
i3 <- draw_indices(strrep("3d", 32), 50, 40)
check("the indices: B rows each, within range, the same for the same seed", identical(dim(i1$m), c(B, 50L)) &&
        identical(dim(i1$f), c(B, 40L)) && all(i1$m >= 1 & i1$m <= 50) && identical(i1, i2) && !identical(i1, i3))
check("the seed's first and eighth hex digits start its two streams", seed_int(s1, 1L) == strtoi("3c3c3c3", 16L) &&
        seed_int(s1, 8L) == strtoi("c3c3c3c", 16L))
check("refuses a seed that is not 64 hex", refused(run("xyz", inputs = tempdir(), results = tempfile())))
check("the JSON writer", {
  f <- tempfile()
  write_json(list(b = 1.5, a = "x\"y", c = list(d = TRUE, e = c(1, NA))), f)
  identical(readLines(f), c("{", '  "a": "x\\"y",', '  "b": 1.5,', '  "c": {"d": true, "e": [1, null]}', "}"))
})
check("the registered test fits the archive's 600 characters", nchar(TEST) <= 600)

# ---------------------------------------------------------------- with bshazard's files: simulated mice only

inputs <- Sys.getenv("CHENG_INPUTS", file.path(here, "..", "inputs"))
have_bsh <- all(file.exists(file.path(inputs, vapply(BSHAZARD, `[[`, "", "name"))))
if (have_bsh) {
  BSH <- load_bshazard(inputs)
  set.seed(11)
  sim <- gompertz_mice(3000, 350, 1.2, FALSE)
  sim$dead[seq(1, 3000, by = 17)] <- 0L
  inp <- binned(sim$age, sim$dead)
  check("the binning totals the deaths and the ages", sum(inp$n.event) == sum(sim$dead) &&
          abs(sum(inp$person.time) - sum(sim$age)) < 1e-9 * sum(sim$age))
  s <- fit_sex(BSH, sim$age, sim$dead)
  b <- BSH$bshazard.default(Surv(age, dead) ~ 1, data = sim, verbose = FALSE)
  check("bshazard() gives the module's hazard", identical(as.vector(b$time), s$X) &&
          isTRUE(all.equal(as.vector(b$hazard), s$hazard, tolerance = 1e-14)))
  check("the spline at the fit's own ages is its hazard", max(abs(log_hazard(BSH, s, s$X) - log(s$hazard))) < 1e-10)
  check("the same mice for both sexes: a ratio of 1", all(abs(ratio_on(BSH, s, s, GRID[GRID >= min(s$X)]) - 1) < 1e-12))
  check("ages outside a fit's span are refused", inherits(tryCatch(log_hazard(BSH, s, max(s$X) + 1), error = function(e) e),
                                                           "error"))
  pl <- planted(BSH, strrep("5a", 32))
  check("the planted peaks are found under a test seed", pl[["350"]]$ok && pl[["600"]]$ok)
} else cat("skip bshazard's files are not at", inputs, "\n")

have_books <- all(file.exists(file.path(inputs, vapply(WORKBOOKS, `[[`, "", "name"))))
if (have_books) {
  for (k in names(WORKBOOKS)) {
    d <- read_workbook(inputs, WORKBOOKS[[k]])
    check(paste(k, "is the pinned file with its rows and groups"), nrow(d) == ROWS[[k]] &&
            setequal(unique(d$group), GROUPS[[k]]))
    ctl <- d[d$group == "Control", ]
    check(paste(k, "holds its controls by sex as pinned"),
          identical(c(m = sum(ctl$sex == "m"), f = sum(ctl$sex == "f")), CONTROLS[[k]]))
  }
} else cat("skip the workbooks are not at", inputs, "\n")

cat(if (failures == 0L) "all passed\n" else sprintf("%d failed\n", failures))
quit(status = if (failures == 0L) 0L else 1L)
