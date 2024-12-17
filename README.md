# Built-Up Growth Rapid Assessment Geoprocessing Tool
> This script is intended to run with .atbx file as an custom geoprocessing tool in ArcGIS Pro.
> I included custom colormap, but you need to set the path to absolute path in your computer. I doesnt know why but it won't work with relative path.

From time series satellite imagery, I expect to be able to automatically:
- Classify and extract built-up areas for each raster independently.
- Create a single raster that shows the overlay of built-up growth.
- Calculate the built-up area and built-up growth rate.
- Assess urban growth elasticity by comparing built-up and population growth
All just in one click.

To create a program capable of accomplishing all objectives in a single execution to optimize efficiency without compromising accuracy. I propose new methods to extract built-up areas quickly. This script combines NDBI, MNDWI, and Modified Index-Based Builtup Index (mIBI) that I developed based on Index-Based Built-up Index (IBI) proposed by Xu (2007)[1].

![image](https://github.com/user-attachments/assets/70debfaa-9cf4-4074-983c-640c4ca2f234)
- mIBI = Mofified Index-Based Built-up Index
- r[Index] = Index rescaled to 0-255

```
 If (mIBI > -0.05 [L8] or 0 [S2]) & (NDBI > MNDWI) then it’s built-up else it’s non-built-up
```
Based on my testing in three different urban agglomerations on Java Island—Cirebon Raya, Semarang, and Malang Raya—the optimal mIBI threshold value is consistently above -0.05 for Landsat 8 and above 0 for Sentinel 2. However, it still interferes with water areas. Therefore, adding the condition that NDBI is greater than MNDWI perfectly excludes water from the results.

While the methods are not scientifically proven (yet), internal testing has shown it achieves 85-92% Overall Accuracy (OA) in the three urban agglomeration areas. Essentially, this is a fun experiment and learning exercise.

After independently extracting built-up areas from each raster, this program will overlay all of them to create a spatiotemporal built-up growth map and calculate built-up growth elasticity by comparing it with population growth data. This elasticity calculation references Cai et al. (2022) to determine the rationality of urban expansion[2].

Feel free to use it for any non-commercial (non-profit) purposes, provided you credit me.
---
[1] Xu, H. (2008). A new index for delineating built‐up land features in satellite imagery. International Journal of Remote Sensing, 29(14), 4269–4276. https://doi.org/10.1080/01431160802039957
[2] Cai, E., Bi, Q., Lu, J., & Hou, H. (2022). The Spatiotemporal Characteristics and Rationality of Emerging Megacity Urban Expansion: A Case Study of Zhengzhou in Central China. Frontiers in Environmental Science, 10. https://doi.org/10.3389/fenvs.2022.860814
