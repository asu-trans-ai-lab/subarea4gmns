# Method

This note sets out the problem and the formulas behind each step: cut, extract, rebuild, assign, check.

## Notation

| Symbol | Meaning |
|---|---|
| $G=(N,A)$ | Reference network: nodes $N$, directed links $A$ |
| $S\subset N$ | Subarea nodes |
| $A_S$ | Links with both ends in $S$ |
| $v_a$ | Reference volume on link $a$ (vehicles in the period) |
| $q_{od}$ | Reference trips from zone $o$ to zone $d$ |
| $Q_{ij}$ | Subarea trips from subarea zone $i$ to $j$ |
| $t_a(v)$ | Link travel time: $t_a(v)=t^0_a\,[1+\alpha_a (v/(C_aH))^{\beta_a}]$ |
| $t^0_a$, $C_a$, $H$ | Free-flow time (minutes), capacity (vehicles per hour), period length (hours) |
| $L_a$ | Length (miles) |

## 1. Cut

A link $a=(u,w)$ is a **crossing** when exactly one of $u,w$ is in $S$; its inside end is a **boundary node** $b$.

- **Subarea network:** every link in $A_S$, plus a boundary centroid $c_b$ for each boundary node, with connectors $c_b\to b$ and $b\to c_b$ in the directions traffic crosses.
- **Zones inside $S$** keep their IDs.
- **Through traffic:** a centroid whose links are all connectors cannot be passed through. A zone on the street network can be, as in Sioux Falls.

## 2. Reference model: user equilibrium

The reference model solves

$$\min_{v}\ \sum_{a\in A}\int_0^{v_a} t_a(x)\,dx\quad\text{s.t. } v \text{ is a feasible loading of } q.$$

It is solved by Frank-Wolfe:

1. Start from the all-or-nothing loading $y^0$ at free-flow times, and set $v^0=y^0$.
2. At iteration $k$, load $y^k$ all-or-nothing on the shortest paths at $t(v^{k-1})$.
3. Find $\lambda_k\in[0,1]$ by bisection on $\sum_a (y^k_a-v^{k-1}_a)\,t_a(v^{k-1}+\lambda(y^k-v^{k-1}))=0$.
4. Set $v^k=(1-\lambda_k)v^{k-1}+\lambda_k y^k$.

**Convergence** is measured by the relative gap

$$\text{gap}=\frac{\sum_a t_a v_a-\sum_a t_a y_a}{\sum_a t_a v_a}.$$

**Shortest paths** are found for all origins at once (SciPy's `dijkstra`). Centroids that cannot be passed through are split into a departure node and an arrival node.

## 3. Extract (paths available)

Unrolling the updates, $v^K=\sum_k w_k\,y^k$ with weights $w_k=\lambda_k\prod_{j>k}(1-\lambda_j)$ (and $\lambda_0=1$). Each $y^k$ sends every trip $q_{od}$ along one path $p^k_{od}$.

**Cutting a path.** Cut $p^k_{od}$ into its maximal runs of links in $A_S$. A run from node $x$ to node $z$ is a subarea trip:

- from zone $o$ if the run starts at the path's origin, otherwise from the boundary centroid $c_x$;
- to zone $d$ if the run ends at the path's destination, otherwise to $c_z$.

Then

$$Q_{ij}=\sum_k w_k \sum_{od}\ q_{od}\ \#\{\text{runs of } p^k_{od} \text{ from } i \text{ to } j\}.$$

**Exactness.** Loading $Q$ on the same runs gives $\sum_k w_k y^k_a = v^K_a$ for every $a\in A_S$.

**Boundary connectors.** A connector's reference volume is the trips that enter or leave there and use subarea links. Traffic that crosses in and straight back out at the same node is not counted.

**Paths from another solver.** With a route file (path, trips), the same cut gives $Q$ directly. This is `extract_from_routes`.

## 4. Rebuild (link volumes only)

Only $v_a$ on $A_S$ and on the connectors is known.

**Supply and demand.** Centroid $i$ has supply $s_i=\sum_{a\in\delta^+(i)} v_a$ and demand $r_i=\sum_{a\in\delta^-(i)} v_a$.

**Precondition.** Flow balances at every other node: $\sum_{a\in\delta^-(n)} v_a=\sum_{a\in\delta^+(n)} v_a$. Nodes that do not balance are reported.

**Path decomposition.** Repeat until $\max_a \text{res}_a\le\varepsilon$:

1. Let $a^*=\arg\max_a \text{res}_a$.
2. Find the fewest-link path $P$ from a centroid $i$ with $s_i>\varepsilon$, through $a^*$, to a centroid $j\ne i$ with $r_j>\varepsilon$. Use only links with $\text{res}>\varepsilon$, and never pass through a centroid.
3. Set $f=\min(\min_{a\in P}\text{res}_a,\ s_i,\ r_j)$.
4. Update $Q_{ij}\mathrel{+}=f$, $\text{res}_a\mathrel{-}=f$ on $P$, $s_i\mathrel{-}=f$, $r_j\mathrel{-}=f$.

**Exactness and limits.**

- On a corridor, where movements between two points share one route, this reproduces every $v_a$.
- On a network with alternative routes, $v$ does not determine the path flows. The decomposition can leave volume unexplained, and the share explained is reported.
- Zones on through nodes have trip ends that link volumes cannot separate from through traffic. They are refused.
- Trips into and out of one centroid through the same access node appear only as a net movement.

## 5. Check

Assign $Q$ on the subarea to user equilibrium. Report, over physical links $a\in A_S$:

$$\text{VMT}=\sum_a v_aL_a,\qquad \text{VHT}=\sum_a \frac{v_a\,t_a(v_a)}{60},\qquad \text{WAPE}=\frac{\sum_a |\hat v_a-v_a|}{\sum_a v_a},$$

together with $R^2$ and the largest link difference, for the subarea assignment $\hat v$ against the reference $v$.

Agreement shows the subarea reproduces the reference model. It says nothing about agreement with observed traffic.
